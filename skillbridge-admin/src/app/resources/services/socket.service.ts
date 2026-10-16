import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';
import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root'
})
export class SocketService {

  private ws: WebSocket | null = null;
  private userId: string | null = null;
  private manuallyDisconnected = false;
  private pendingFrames: string[] = [];
  readonly events$ = new Subject<any>();

  connect(userId: string): void {
    this.userId = userId;
    this.manuallyDisconnected = false;
    if (
      this.ws &&
      (
        this.ws.readyState === WebSocket.OPEN ||
        this.ws.readyState === WebSocket.CONNECTING
      )
    ) {
      return;
    }

    const token = localStorage.getItem('access_token');

    if (!token) {
      console.error('Cannot connect WebSocket: no access token');
      return;
    }

    const wsUrl =
      `${environment.wsUrl}chat/ws/${userId}?token=${encodeURIComponent(token)}`;

    console.log('Connecting Admin WebSocket...');

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('Admin WebSocket Connected');
      const frames = this.pendingFrames.splice(0);
      frames.forEach(frame => this.ws?.send(frame));
    };

    this.ws.onmessage = (event) => {
      try {
        this.events$.next(JSON.parse(event.data));
      } catch {
        console.error('Invalid admin WebSocket message');
      }
    };

    this.ws.onclose = (event) => {
      console.log(
        'Admin WebSocket Disconnected',
        'code:', event.code,
        'reason:', event.reason
      );

      this.ws = null;
      if (!this.manuallyDisconnected && this.userId && localStorage.getItem('access_token')) {
        setTimeout(() => this.userId && this.connect(this.userId), 1000);
      }
    };

    this.ws.onerror = (error) => {
      console.error('Admin WebSocket error:', error);
    };
  }

  disconnect(): void {
    this.manuallyDisconnected = true;
    this.userId = null;
    this.pendingFrames = [];
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  sendMessage(chatRoomId: string, content: string): boolean {
    const frame = JSON.stringify({
      type: 'send_message',
      payload: {
        chat_room_id: chatRoomId,
        content,
        client_message_id: crypto.randomUUID()
      }
    });
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(frame);
      return true;
    }
    if (!this.userId || !localStorage.getItem('access_token')) {
      return false;
    }
    this.pendingFrames.push(frame);
    if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
      this.connect(this.userId);
    }
    return true;
  }
}

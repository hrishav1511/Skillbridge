import { Injectable } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ChatMessage } from '../models';

@Injectable({
  providedIn: 'root'
})
export class ChatService {

  private ws!: WebSocket | null;
  private userId: string | null = null;
  private manuallyDisconnected = false;
  private pendingFrames: string[] = [];

  public events$ = new Subject<any>();
  private readonly newMessageSubject = new Subject<ChatMessage>();
  readonly newMessage$ = this.newMessageSubject.asObservable();
  private readonly activeChatRoomSubject = new BehaviorSubject<string | null>(null);
  readonly activeChatRoom$ = this.activeChatRoomSubject.asObservable();
  connect(userId: string): boolean {

  this.userId = userId;
  this.manuallyDisconnected = false;

  if (
    this.ws &&
    (
      this.ws.readyState === WebSocket.OPEN ||
      this.ws.readyState === WebSocket.CONNECTING
    )
  ) {
    return true;
  }

  const token = localStorage.getItem('access_token');

  if (!token) {
    return false;
  }

  const wsUrl =
    `${environment.wsUrl}chat/ws/${userId}?token=${encodeURIComponent(token)}`;

  console.log('Connecting WebSocket...');

  this.ws = new WebSocket(wsUrl);

  this.ws.onopen = () => {
    console.log('Chat Connected');
    const frames = this.pendingFrames.splice(0);
    frames.forEach(frame => this.ws?.send(frame));
  };

  this.ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log(' Parsed WebSocket data:', data);
      this.events$.next(data);
      if (data.event === 'new_message' && data.payload) {
        this.newMessageSubject.next(data.payload as ChatMessage);
      }
    } catch (error) {
      console.error('Invalid WebSocket message:', event.data);
    }
  };

  this.ws.onclose = (event) => {
    console.log(
      'Chat Disconnected',
      'code:', event.code,
      'reason:', event.reason
    );

    this.ws = null;
    if (!this.manuallyDisconnected && this.userId && localStorage.getItem('access_token')) {
      setTimeout(() => this.userId && this.connect(this.userId), 1000);
    }
  };

  this.ws.onerror = (err) => {
    console.error('WebSocket error:', err);
  };
  return true;
}
  disconnect(): void {
    this.manuallyDisconnected = true;
    this.userId = null;
    this.pendingFrames = [];
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.activeChatRoomSubject.next(null);
  }

  setActiveChatRoom(chatRoomId: string | null): void {
    this.activeChatRoomSubject.next(chatRoomId);
  }

  private getCurrentUserId(): string {
    try {
      return JSON.parse(localStorage.getItem('user_id') || 'null') || '';
    } catch {
      return localStorage.getItem('user_id') || '';
    }
  }

  private send(type: string, payload: any): boolean {
    const frame = JSON.stringify({ type, payload });
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

  fetchHistory(chatRoomId: string): void {

    this.send('fetch_history', {
      chat_room_id: chatRoomId,
      limit: 30
    });
  }

  sendMessage(
    chatRoomId: string,
    content: string
  ): boolean {

    return this.send('send_message', {
      chat_room_id: chatRoomId,
      content,
      client_message_id: crypto.randomUUID()
    });
  }

  markRead(
    chatRoomId: string,
    messageId: string
  ): void {

    this.send('mark_read', {
      chat_room_id: chatRoomId,
      message_id: messageId
    });
  }

  setTyping(
    chatRoomId: string,
    isTyping: boolean
  ): void {

    this.send('typing', {
      chat_room_id: chatRoomId,
      is_typing: isTyping
    });
  }
}

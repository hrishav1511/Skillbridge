import { Component, OnDestroy, OnInit } from '@angular/core';
import { Subject, Subscription } from 'rxjs';
import { ChatMessage, Notification } from '../models';
import { ChatService } from '../services/socket.service';
import { NotificationService } from '../services/notification.service';
import { NotificationRoutingService } from '../services/notification-routing.service';

@Component({
  selector: 'app-notification-popup',
  templateUrl: './notification-popup.component.html',
  styleUrls: ['./notification-popup.component.scss']
})
export class NotificationPopupComponent implements OnInit, OnDestroy {
  currentNotification: Notification | null = null;
  currentChatMessage: ChatMessage | null = null;

  private readonly notificationQueue: Notification[] = [];
  private readonly dismiss$ = new Subject<void>();
  private notificationSubscription?: Subscription;
  private chatMessageSubscription?: Subscription;
  private activeRoomSubscription?: Subscription;
  private activeChatRoomId: string | null = null;
  private dismissSubscription?: Subscription;
  private dismissTimer?: number;

  constructor(
    private notificationService: NotificationService,
    private chatService: ChatService,
    private notificationRouting: NotificationRoutingService
  ) {}

  /** Follow the toast to whatever it is about, then dismiss it. */
  openCurrent(): void {
    if (!this.currentNotification) {
      return;
    }
    const notification = this.currentNotification;
    this.close();
    this.notificationRouting.open(notification);
  }

  get currentIsNavigable(): boolean {
    return this.notificationRouting.isNavigable(this.currentNotification);
  }

  ngOnInit(): void {
    this.notificationSubscription = this.notificationService.newNotification$.subscribe(notification => {
      this.notificationQueue.push(notification);
      this.showNextNotification();
    });

    this.activeRoomSubscription = this.chatService.activeChatRoom$.subscribe(roomId => {
      this.activeChatRoomId = roomId;
    });
    this.chatMessageSubscription = this.chatService.newMessage$.subscribe(message => {
      if (message.chat_room_id === this.activeChatRoomId) {
        return;
      }
      this.currentChatMessage = message;
      this.currentNotification = null;
      this.resetDismissTimer();
    });

    this.dismissSubscription = this.dismiss$.subscribe(() => {
      this.currentNotification = null;
      this.showNextNotification();
    });
  }

  close(): void {
    this.resetDismissTimer();
    this.currentChatMessage = null;
    this.dismiss$.next();
  }

  ngOnDestroy(): void {
    this.notificationSubscription?.unsubscribe();
    this.chatMessageSubscription?.unsubscribe();
    this.activeRoomSubscription?.unsubscribe();
    this.dismissSubscription?.unsubscribe();
  }

  private resetDismissTimer(): void {
    if (this.dismissTimer) {
      window.clearTimeout(this.dismissTimer);
    }
    this.dismissTimer = window.setTimeout(() => this.close(), 5000);
  }

  private showNextNotification(): void {
    if (this.currentNotification || this.notificationQueue.length === 0) {
      return;
    }

    this.currentNotification = this.notificationQueue.shift() || null;

    if (this.currentNotification) {
      this.resetDismissTimer();
    }
  }
}

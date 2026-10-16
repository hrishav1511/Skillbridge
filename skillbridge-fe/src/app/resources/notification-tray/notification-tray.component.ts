import { Component, OnDestroy, OnInit } from '@angular/core';
import { Subscription } from 'rxjs';
import { Notification } from '../models';
import { NotificationService } from '../services/notification.service';
import { NotificationRoutingService } from '../services/notification-routing.service';

@Component({
  selector: 'app-notification-tray',
  templateUrl: './notification-tray.component.html',
  styleUrls: ['./notification-tray.component.scss']
})
export class NotificationTrayComponent implements OnInit, OnDestroy {
  notifications: Notification[] = [];
  loading = true;
  unreadOnly = false;
  isGuest = false;
  private notificationSubscription?: Subscription;

  constructor(
    private notificationService: NotificationService,
    private notificationRouting: NotificationRoutingService
  ) {}

  ngOnInit(): void {
    const user = JSON.parse(localStorage.getItem('userData') || '{}');
    this.isGuest = user.role === 'guest';

    if (this.isGuest) {
      this.loading = false;
      return;
    }

    this.loadNotifications();
    this.notificationSubscription = this.notificationService.newNotification$.subscribe(notification => {
      // The service already drops replays, but a live arrival can still
      // race the history load; keep the list keyed by id regardless.
      this.notifications = [
        notification,
        ...this.notifications.filter(item => item.id !== notification.id)
      ];
    });
  }

  ngOnDestroy(): void {
    this.notificationSubscription?.unsubscribe();
  }

  loadNotifications(): void {
    this.loading = true;
    this.notificationService.getNotifications(50, 0, this.unreadOnly).subscribe({
      next: response => {
        this.notifications = response.data || [];
        // History: these ids must not be re-announced by the socket.
        this.notificationService.registerKnown(this.notifications);
        this.loading = false;
      },
      error: () => {
        this.notifications = [];
        this.loading = false;
      }
    });
  }

  setUnreadOnly(unreadOnly: boolean): void {
    if (this.unreadOnly === unreadOnly) {
      return;
    }
    this.unreadOnly = unreadOnly;
    this.loadNotifications();
  }

  markAsRead(notification: Notification): void {
    if (notification.is_read) {
      return;
    }
    this.notificationService.markAsRead(notification.id).subscribe({
      next: () => notification.is_read = true
    });
  }

  /** Mark the notification read, then go to whatever it is about. */
  openNotification(notification: Notification): void {
    this.markAsRead(notification);
    this.notificationRouting.open(notification);
  }

  isNavigable(notification: Notification): boolean {
    return this.notificationRouting.isNavigable(notification);
  }

  markAllAsRead(): void {
    if (!this.unreadCount) {
      return;
    }
    this.notificationService.markAllAsRead().subscribe({
      next: () => this.notifications.forEach(notification => notification.is_read = true)
    });
  }

  get unreadCount(): number {
    return this.notifications.filter(notification => !notification.is_read).length;
  }
}
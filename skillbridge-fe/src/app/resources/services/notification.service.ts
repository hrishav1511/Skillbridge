import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';
import { ChatService } from './socket.service';
import { Subject } from 'rxjs';
import { Notification, NotificationListResponse } from '../models';

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private readonly newNotificationSubject = new Subject<Notification>();

  /*
   * Ids already accounted for, from either source.
   *
   * On connect the server replays every undelivered notification over the
   * socket while the list API returns the same rows as history, so without
   * this the tray showed each one twice and the popup re-announced old news.
   * The rule: the list API supplies history, the socket supplies live
   * additions only - anything already known is dropped here rather than in
   * each subscriber.
   */
  private readonly seenIds = new Set<string>();
  readonly newNotification$ = this.newNotificationSubject.asObservable();

  constructor(
    private http: HttpClient,
    private chatService: ChatService
  ) { }


  getNotifications(
  limit: number = 50,
  offset: number = 0,
  unreadOnly: boolean = false
) {
  return this.http.get<NotificationListResponse>(
    environment.apiUrl + 'notifications/',
    {
      params: {
        limit,
        offset,
        unread_only: unreadOnly
      }
    }
  );
}

markAsRead(notificationId: string) {
  return this.http.patch<Notification>(
    environment.apiUrl + `notifications/${notificationId}/read/`,
    {}
  );
}

markAllAsRead() {
  return this.http.patch<{ 
    success: boolean;
    message: string;
    data: {
      updated_count: number;
    };
  }>(
    environment.apiUrl + 'notifications/read-all/',
    {}
  );
}
listenForNotifications() {
  console.log(' Notification service is listening for notifications...');

  return this.chatService.events$.subscribe((event) => {
    if (event.event === 'notification') {
    const notification = event.payload as Notification;
    console.log('NOTIFICATION RECEIVED:', notification);
    if (this.isAlreadyKnown(notification)) {
      return;
    }
    this.newNotificationSubject.next(notification);
    }

  });
}

/**
 * Record notifications that came from the list API as history.
 *
 * Anything registered here will not be re-emitted if the socket replays it.
 */
registerKnown(notifications: Notification[] | null | undefined): void {
  (notifications || []).forEach(notification => {
    if (notification?.id) {
      this.seenIds.add(String(notification.id));
    }
  });
}

/** True when this notification has already been seen from either source. */
private isAlreadyKnown(notification: Notification | null | undefined): boolean {
  const id = notification?.id ? String(notification.id) : '';
  if (!id) {
    // No id means it cannot be de-duplicated; let it through rather than
    // silently swallowing a real notification.
    return false;
  }
  if (this.seenIds.has(id)) {
    return true;
  }
  this.seenIds.add(id);
  return false;
}
}

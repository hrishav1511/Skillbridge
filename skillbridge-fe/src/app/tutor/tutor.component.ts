import { Component, HostListener, OnDestroy, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { NavigationStart } from '@angular/router';
import { finalize, Subscription } from 'rxjs';
import { environment } from '../../environments/environment';
import { Notification } from '../resources/models';
import { NotificationService } from '../resources/services/notification.service';
import { NotificationRoutingService } from '../resources/services/notification-routing.service';
import { ProfileImageService } from '../resources/services/profile-image.service';
import { ChatService } from '../resources/services/socket.service';
import { UnreadMessagesService } from '../resources/services/unread-messages.service';

@Component({
  selector: 'app-tutor',
  templateUrl: './tutor.component.html',
  styleUrls: ['./tutor.component.scss']
})
export class TutorComponent implements OnInit, OnDestroy {

  showProfileMenu = false;
  mobileMenuOpen = false;
  notifications: Notification[] = [];
  loggedInUser: any = {};
  profileImage: string | null = null;
  private notificationSubscription?: Subscription;
  private notificationSocketSubscription?: Subscription;
  private profileImageSubscription?: Subscription;
  private routerSubscription?: Subscription;
  private unreadSubscription?: Subscription;
  unreadConversations = 0;
  constructor(
    private route:Router,
    private notificationService: NotificationService,
    private profileImageService: ProfileImageService,
    private chatService:ChatService,
    private http: HttpClient,
    private notificationRouting: NotificationRoutingService,
    private unreadMessages: UnreadMessagesService
    ) {}
    ngOnInit(): void {
      this.loggedInUser = JSON.parse(localStorage.getItem('userData') || '{}');
      this.getNotification()
      this.unreadMessages.start();
      this.unreadSubscription = this.unreadMessages.unreadConversations$
        .subscribe(count => this.unreadConversations = count);
      this.notificationSubscription = this.notificationService.newNotification$.subscribe(notification => {
        this.notifications = [
          notification,
          ...this.notifications.filter(item => item.id !== notification.id)
        ].slice(0, 5);
      });
      this.profileImageSubscription = this.profileImageService.profileImage$.subscribe(profileImage => {
        this.profileImage = profileImage;
      });
      this.routerSubscription = this.route.events.subscribe(event => {
        if (event instanceof NavigationStart) {
          this.closeMenus();
        }
      });
      const userData = localStorage.getItem('user_id');

    if (userData && localStorage.getItem('access_token')) {
      const user = JSON.parse(userData);

      if (this.chatService.connect(user)) {
        this.notificationSocketSubscription = this.notificationService.listenForNotifications();
      }
    }
    }

    ngOnDestroy(): void {
      this.notificationSubscription?.unsubscribe();
      this.notificationSocketSubscription?.unsubscribe();
      this.profileImageSubscription?.unsubscribe();
      this.routerSubscription?.unsubscribe();
      this.unreadSubscription?.unsubscribe();
    }

    @HostListener('document:click', ['$event'])
    closeProfileOnOutsideClick(event: MouseEvent): void {
      const target = event.target as HTMLElement;
      if (!target.closest('.profile-menu')) {
        this.showProfileMenu = false;
      }
    }

    closeMenus(): void {
      this.showProfileMenu = false;
      this.mobileMenuOpen = false;
    }

    /** Follow a navbar notification to whatever it refers to. */
    openNotification(notification: Notification): void {
      this.notificationRouting.open(notification);
    }

  logout(){
    this.closeMenus();
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      this.finishLogout();
      return;
    }
    this.http.post(environment.apiUrl + 'user/logout/', { refresh_token: refreshToken }).pipe(
      finalize(() => this.finishLogout())
    ).subscribe({ error: () => undefined });
  }

  private finishLogout(): void {
    localStorage.clear();
    this.chatService.disconnect();
    this.route.navigateByUrl('auth/login');
  }

   getNotification(){
      
      this.notificationService.getNotifications().subscribe({
        next: (response) => {
          this.notifications = response.data.slice(0, 5);
          // History: these must not be re-announced by the socket.
          this.notificationService.registerKnown(response.data);
        },
        error: (error) => {
          console.error(' NOTIFICATION REST ERROR:', error);
        }
      });
    }
}

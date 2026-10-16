import { Component, HostListener, OnDestroy, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { finalize, Subscription } from 'rxjs';
import { ToastrService } from 'ngx-toastr';
import { environment } from '../../../environments/environment';
import { apiLists } from '../../resources/apiLists';
import { Notification } from '../../resources/models';
import { NotificationService } from '../../resources/services/notification.service';
import { NotificationRoutingService } from '../../resources/services/notification-routing.service';
import { UnreadMessagesService } from '../../resources/services/unread-messages.service';
import { ChatService } from '../../resources/services/socket.service';

@Component({
  selector: 'app-student',
  templateUrl: './student.component.html',
  styleUrls: ['./student.component.scss']
})
export class StudentComponent implements OnInit, OnDestroy {

  loggedInUser: any | null;
  unreadConversations = 0;
  mobileMenuOpen = false;
  profileTrayOpen = false;
  profileImage: string | null = null;
  profilePhotoBusy = false;
  private studentId = '';
  notifications: Notification[] = [];
  private notificationSubscription?: Subscription;
  private unreadSubscription?: Subscription;
  private notificationSocketSubscription?: Subscription;
  constructor(
    private router: Router,
    private notificationService: NotificationService,
    private chatService: ChatService,
    private http: HttpClient,
    private toastr: ToastrService,
    private notificationRouting: NotificationRoutingService,
    private unreadMessages: UnreadMessagesService
    // private Route:Route
  ) {
    this.loggedInUser = JSON.parse(localStorage.getItem('userData') || '{}');
    this.studentId = localStorage.getItem('student_id') || '';
    this.profileImage = this.loggedInUser?.profile_picture_url || this.loggedInUser?.profile_image || null;

  }

  ngOnInit(): void {
    if (this.loggedInUser['role'] !== 'guest' ) {
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
    }
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
    this.unreadSubscription?.unsubscribe();
    this.notificationSocketSubscription?.unsubscribe();
  }

  @HostListener('document:click', ['$event'])
  closeProfileTrayOnOutsideClick(event: MouseEvent): void {
    const target = event.target as HTMLElement;
    if (!target.closest('.student-profile-menu')) {
      this.profileTrayOpen = false;
    }
  }

  get studentInitials(): string {
    const name = this.loggedInUser?.full_name?.trim() || 'Student';
    return name.split(/\s+/).slice(0, 2).map((part: string) => part[0]).join('').toUpperCase();
  }

  toggleProfileTray(event?: Event): void {
    event?.stopPropagation();
    this.profileTrayOpen = !this.profileTrayOpen;
  }

  onProfilePhotoSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file || !this.studentId || this.loggedInUser?.role === 'guest') return;

    const formData = new FormData();
    formData.append('file', file);
    this.profilePhotoBusy = true;
    this.http.post<any>(environment.apiUrl + apiLists.student_profile_picture_update + this.studentId + '/upload-profile-picture/', formData).subscribe({
      next: (response) => {
        const uploadedImage = response?.profile_picture_url || response?.data?.profile_picture_url || response?.url;
        this.updateStoredProfileImage(uploadedImage || URL.createObjectURL(file));
        this.profilePhotoBusy = false;
        input.value = '';
        this.toastr.success('Profile photo updated');
      },
      error: () => {
        this.profilePhotoBusy = false;
        input.value = '';
        this.toastr.error('Unable to update profile photo');
      }
    });
  }

  removeProfilePhoto(): void {
    if (!this.studentId || !this.profileImage || this.loggedInUser?.role === 'guest') return;

    this.profilePhotoBusy = true;
    this.http.delete(environment.apiUrl + apiLists.student_profile_picture_remove + this.studentId + '/profile-picture/').subscribe({
      next: () => {
        this.updateStoredProfileImage(null);
        this.profilePhotoBusy = false;
        this.toastr.success('Profile photo removed');
      },
      error: () => {
        this.profilePhotoBusy = false;
        this.toastr.error('Unable to remove profile photo');
      }
    });
  }

  /** Follow a navbar notification to whatever it refers to. */
  openNotification(notification: any): void {
    this.notificationRouting.open(notification);
  }

  private updateStoredProfileImage(profileImage: string | null): void {
    this.profileImage = profileImage;
    this.loggedInUser = { ...this.loggedInUser, profile_picture_url: profileImage, profile_image: profileImage };
    localStorage.setItem('userData', JSON.stringify(this.loggedInUser));
  }

  logout() {
    this.mobileMenuOpen = false;
    this.profileTrayOpen = false;
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
    this.router.navigateByUrl('auth/login');
  }

  getNotification() {

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

import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { Notification } from '../models';

/**
 * Works out where a notification should take the user when it is clicked.
 *
 * Every notification the API sends already carries the entity it refers to in
 * its `data` payload, so no extra field was needed on the wire - the mapping
 * from type plus entity to a route lives here, shared by the notification tray,
 * the toast popup and the navbar dropdowns.
 */
@Injectable({
  providedIn: 'root'
})
export class NotificationRoutingService {

  constructor(private router: Router) {}

  /** The current user's role, as stored at login. */
  private role(): 'student' | 'tutor' {
    return (localStorage.getItem('user_ROLE') || '').toUpperCase() === 'TUTOR'
      ? 'tutor'
      : 'student';
  }

  /** The dashboard for whoever is signed in; also used for the logo link. */
  dashboardRoute(): string {
    return this.role() === 'tutor' ? '/tutor/dashboard' : '/student/dashboard';
  }

  /**
   * The route a notification points at, or null when it refers to nothing
   * navigable (in which case the caller should leave it inert rather than
   * navigating somewhere arbitrary).
   */
  routeFor(notification: Notification | null | undefined): any[] | null {
    if (!notification) {
      return null;
    }
    const data = notification.data || {};
    const isTutor = this.role() === 'tutor';

    switch (notification.notification_type) {
      case 'CHAT_MESSAGE_RECEIVED':
        return isTutor ? ['/tutor/my-messages'] : ['/student/chats'];

      case 'SESSION_REQUESTED':
      case 'SESSION_ACCEPTED':
      case 'SESSION_DECLINED':
      case 'SESSION_CANCELLED':
      case 'RESCHEDULE_PROPOSED':
        if (isTutor) {
          return data.service_id
            ? ['/tutor/service-dashboard', data.service_id]
            : ['/tutor/dashboard'];
        }
        return ['/student/booked-services'];

      case 'SERVICE_UPDATED':
      case 'SERVICE_REVIEW_CREATED':
      case 'SERVICE_REPORTED':
      case 'SERVICE_DISABLED_AFTER_REPORT':
        if (isTutor) {
          return data.service_id
            ? ['/tutor/services', data.service_id]
            : ['/tutor/services'];
        }
        return ['/student/dashboard'];

      case 'TUTOR_PROFILE_APPROVED':
      case 'TUTOR_PROFILE_REJECTED':
        return ['/tutor/my-profile'];

      case 'TUTOR_REVIEW_CREATED':
      case 'TUTOR_REPORTED':
      case 'TUTOR_DISABLED_AFTER_REPORT':
        if (isTutor) {
          return ['/tutor/my-profile'];
        }
        return data.tutor_id
          ? ['/student/dashboard/view-tutor', data.tutor_id]
          : ['/student/dashboard'];

      case 'REVIEW_REPORTED':
      case 'REVIEW_REMOVED':
      case 'REVIEW_REPORT_DISMISSED':
        return isTutor ? ['/tutor/my-profile'] : ['/student/dashboard'];

      default:
        return null;
    }
  }

  /** True when clicking the notification will go somewhere. */
  isNavigable(notification: Notification | null | undefined): boolean {
    return this.routeFor(notification) !== null;
  }

  /** Navigate to the notification's target, if it has one. */
  open(notification: Notification | null | undefined): void {
    const route = this.routeFor(notification);
    if (route) {
      this.router.navigate(route);
    }
  }
}

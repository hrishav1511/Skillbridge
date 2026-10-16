import { Component, OnDestroy, OnInit } from '@angular/core';
import { environment } from '../../../environments/environment';
import { apiLists } from '../../resources/apiLists';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { Dialog } from '@angular/cdk/dialog';
import {
  RescheduleDialogComponent,
  RescheduleDialogResult
} from '../../resources/Modals/reschedule-dialog/reschedule-dialog.component';
import { ReviewsComponent } from '../../resources/Modals/reviews/reviews.component';
import { CancelBookingComponent } from '../../resources/Modals/cancel-booking/cancel-booking.component';

@Component({
  selector: 'app-services-list',
  templateUrl: './services-list.component.html',
  styleUrls: ['./services-list.component.scss']
})
export class ServicesListComponent implements OnInit, OnDestroy {
  booked_service_list: any[] = [];
  attachmentsByService: { [serviceId: string]: any[] } = {};
  expandedResources: { [serviceId: string]: boolean } = {};
  loadingAttachments: { [serviceId: string]: boolean } = {};
  cancellingBookings: { [bookingId: string]: boolean } = {};
  student_ID: any = localStorage.getItem('student_id');
  currentUserId: string | null = JSON.parse(localStorage.getItem('user_id') || 'null');
  countdownTick = 0;
  private countdownTimer?: ReturnType<typeof setInterval>;

  constructor(
    private http: HttpClient,
    private route: Router,
    private activatedRoute: ActivatedRoute,
    private toastr: ToastrService,
    private dialog:Dialog
  ) {}

  ngOnInit(): void {
    this.getBookings();
    this.countdownTimer = setInterval(() => this.countdownTick++, 1000);
  }

  ngOnDestroy(): void {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
    }
  }

  getBookings() {
    const params = new URLSearchParams();
    params.set('student_id', this.student_ID);
    this.http.get(environment.apiUrl + apiLists.get_booked_services + '?' + params).subscribe({
      next: (res: any) => {
        this.booked_service_list = res?.data || [];
        this.booked_service_list.forEach(item => this.loadAttachments(item));
        this.scrollToRequestedService();
      },
      error: () => this.toastr.error('Unable to load your booked services.')
    });
  }

  serviceAnchorId(item: any): string {
    return `service-card-${this.bookingId(item)}`;
  }

  private scrollToRequestedService(): void {
    const requestedServiceId = this.activatedRoute.snapshot.queryParamMap.get('serviceId');
    if (!requestedServiceId) {
      return;
    }

    setTimeout(() => {
      document.getElementById(`service-card-${requestedServiceId}`)?.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    });
  }

  private loadAttachments(item: any): void {
    const service = item?.service;
    const serviceId = service?.id;
    if (!serviceId) {
      return;
    }

    if (Array.isArray(service.attachments)) {
      this.attachmentsByService[serviceId] = service.attachments;
      return;
    }

    this.loadingAttachments[serviceId] = true;
    this.http.get<any>(environment.apiUrl + apiLists.attachment_list_upload + serviceId + '/attachments/').subscribe({
      next: (response) => this.attachmentsByService[serviceId] = response?.data || [],
      error: () => this.attachmentsByService[serviceId] = []
    }).add(() => this.loadingAttachments[serviceId] = false);
  } 

  openReviewModal(item: any): void {
      /*
       * The review is filed against the tutor, so this must be the tutors-row
       * id. `item.tutor.user.id` is the tutor's *user* id and produced reviews
       * pointed at a tutor that does not exist.
       */
      const tutorId = item?.tutor?.id ?? item?.service?.tutor_id ?? null;
      const dialog = this.dialog.open(ReviewsComponent, {
        height: '100%',
        panelClass: 'profile-drawer',
        data: {
          type: 'service',
          student_id: this.student_ID,
          tutor_id: tutorId,
          service: item?.service || null
        }
      });
    }

  serviceMedia(item: any): Array<{ type: 'image' | 'video'; url: string }> {
    const service = item?.service;
    if (!service) {
      return [];
    }

    const imageUrls = Array.isArray(service.image_urls) ? service.image_urls.filter((url: string | null | undefined) => !!url) : [];
    const videoUrls = Array.isArray(service.video_urls) ? service.video_urls.filter((url: string | null | undefined) => !!url) : [];
    const singleVideoUrl = service.video_url ? [service.video_url] : [];
    const allVideoUrls = [...videoUrls, ...singleVideoUrl.filter((url: string) => !videoUrls.includes(url))];

    return [
      ...imageUrls.map((url: string) => ({ type: 'image' as const, url })),
      ...allVideoUrls.map((url: string) => ({ type: 'video' as const, url }))
    ];
  }

  currentMediaIndexByService: { [serviceId: string]: number } = {};
  expandedMediaByService: { [serviceId: string]: boolean } = {};

  isMediaExpanded(item: any): boolean {
    return !!this.expandedMediaByService[item?.service?.id];
  }

  toggleMedia(item: any): void {
    const serviceId = item?.service?.id;
    if (serviceId) {
      this.expandedMediaByService[serviceId] = !this.isMediaExpanded(item);
    }
  }

  currentMedia(item: any): { type: 'image' | 'video'; url: string } | null {
    const serviceId = item?.service?.id;
    const media = this.serviceMedia(item);
    if (!serviceId || !media.length) {
      return null;
    }

    const currentIndex = this.currentMediaIndexByService[serviceId] ?? 0;
    const safeIndex = ((currentIndex % media.length) + media.length) % media.length;
    this.currentMediaIndexByService[serviceId] = safeIndex;
    return media[safeIndex];
  }

  setMediaIndex(item: any, index: number): void {
    const serviceId = item?.service?.id;
    const media = this.serviceMedia(item);
    if (!serviceId || !media.length) {
      return;
    }

    this.currentMediaIndexByService[serviceId] = ((index % media.length) + media.length) % media.length;
  }

  moveMedia(item: any, direction: number): void {
    const serviceId = item?.service?.id;
    const media = this.serviceMedia(item);
    if (!serviceId || !media.length) {
      return;
    }

    const currentIndex = this.currentMediaIndexByService[serviceId] ?? 0;
    const nextIndex = (currentIndex + direction + media.length) % media.length;
    this.currentMediaIndexByService[serviceId] = nextIndex;
  }

  attachmentsFor(item: any): any[] {
    return this.attachmentsByService[item?.service?.id] || [];
  }

  visibleAttachments(item: any): any[] {
    const attachments = this.attachmentsFor(item);
    return this.isResourcesExpanded(item) ? attachments : attachments.slice(0, 4);
  }

  isResourcesExpanded(item: any): boolean {
    return !!this.expandedResources[item?.service?.id];
  }

  toggleResources(item: any): void {
    const serviceId = item?.service?.id;
    if (serviceId) {
      this.expandedResources[serviceId] = !this.isResourcesExpanded(item);
    }
  }

  serviceStart(item: any): Date | null {
    if (item?.scheduled_start_at) {
      const scheduled = new Date(item.scheduled_start_at);
      return Number.isNaN(scheduled.getTime()) ? null : scheduled;
    }
    if (!item?.service?.date) {
      return null;
    }

    const dateTime = `${item.service.date}T${item.service.time || '00:00:00'}`;
    const start = new Date(dateTime);
    return Number.isNaN(start.getTime()) ? null : start;
  }

  serviceEnd(item: any): Date | null {
    const scheduledStart = this.serviceStart(item);
    if (scheduledStart && item?.service?.time && item?.service?.end_time) {
      const [startHours, startMinutes] = item.service.time.split(':').map(Number);
      const [endHours, endMinutes] = item.service.end_time.split(':').map(Number);
      const durationMinutes = Math.max(0, (endHours * 60 + endMinutes) - (startHours * 60 + startMinutes));
      return new Date(scheduledStart.getTime() + durationMinutes * 60000);
    }
    if (!item?.service?.date) {
      return null;
    }

    const endTime = item?.service?.end_time || item?.service?.time || '00:00:00';
    const dateTime = `${item.service.date}T${endTime}`;
    const end = new Date(dateTime);
    return Number.isNaN(end.getTime()) ? null : end;
  }

  formatServiceTimeRange(item: any): string {
    const scheduledStart = this.serviceStart(item);
    if (scheduledStart) {
      return scheduledStart.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    const start = item?.service?.time ? item.service.time.slice(0, 5) : '00:00';
    const end = item?.service?.end_time ? item.service.end_time.slice(0, 5) : null;
    return end ? `${start} - ${end}` : start;
  }

  isUpcoming(item: any): boolean {
    const start = this.serviceStart(item);
    return !!start && start.getTime() > Date.now();
  }

  isFinished(item: any): boolean {
    const end = this.serviceEnd(item);
    return !!end && end.getTime() <= Date.now();
  }

  /**
   * A service can be joined only while it is actually running.
   *
   * This used to be "not upcoming", which stayed true forever once the start
   * time passed - so a service from last month still offered a Join button.
   * The backend withholds the link for a finished service as well, so this is
   * a disabled control rather than the only guard.
   */
  canJoin(item: any): boolean {
    return this.bookingStatus(item) === 'ACCEPTED'
      && !this.isUpcoming(item)
      && !this.isFinished(item)
      && !!item?.service?.joining_link;
  }

  isReviewAvailable(item: any): boolean {
    const end = this.serviceEnd(item);
    return this.bookingStatus(item) === 'ACCEPTED' && !!end && end.getTime() <= Date.now();
  }

  countdown(item: any): string {
    const start = this.serviceStart(item);
    if (!start) {
      return 'Schedule unavailable';
    }

    const remaining = start.getTime() - Date.now();
    if (remaining <= 0) {
      return 'Starting now';
    }

    const totalMinutes = Math.floor(remaining / 60000);
    const days = Math.floor(totalMinutes / 1440);
    const hours = Math.floor((totalMinutes % 1440) / 60);
    const minutes = totalMinutes % 60;
    const seconds = Math.floor((remaining % 60000) / 1000);

    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    }
    return `${hours}h ${minutes}m ${seconds}s`;
  }

  bookingId(item: any): any {
    return item?.id || item?.booking_id;
  }

  bookingStatus(item: any): string {
    return String(item?.status || item?.booking_status || 'PENDING').toUpperCase();
  }

  canCancel(item: any): boolean {
    return ['PENDING', 'ACCEPTED'].includes(this.bookingStatus(item)) && this.isUpcoming(item);
  }

  canReschedule(item: any): boolean {
    return this.bookingStatus(item) === 'ACCEPTED' && this.isUpcoming(item) && !this.pendingProposal(item);
  }

  pendingProposal(item: any): any | null {
    return (item?.reschedule_proposals || []).find((proposal: any) => proposal.proposal_status === 'PENDING') || null;
  }

  canRespondToProposal(item: any): boolean {
    const proposal = this.pendingProposal(item);
    return !!proposal && proposal.proposed_by_user_id !== this.currentUserId;
  }

  proposeReschedule(item: any): void {
    const bookingId = this.bookingId(item);
    if (!bookingId) {
      return;
    }

    const dialogRef = this.dialog.open<RescheduleDialogResult>(RescheduleDialogComponent, {
      panelClass: ['profile-drawer'],
      data: {
        currentStartAt: item?.scheduled_start_at,
        serviceName: item?.service?.service_name
      }
    });

    dialogRef.closed.subscribe((result) => {
      if (!result?.proposedStartAt) {
        return;
      }
      this.http.post(
        `${environment.apiUrl}${apiLists.booking_reschedule}${bookingId}/reschedule/`,
        { proposed_start_at: result.proposedStartAt }
      ).subscribe({
        next: () => {
          this.toastr.success('Reschedule proposal sent.');
          this.getBookings();
        },
        error: (error) => this.toastr.error(error?.error?.detail || 'Unable to propose a new time.')
      });
    });
  }

  respondToProposal(item: any, accept: boolean): void {
    const bookingId = this.bookingId(item);
    const proposal = this.pendingProposal(item);
    if (!bookingId || !proposal?.id) {
      return;
    }
    const action = accept ? 'accept' : 'reject';
    this.http.patch(
      `${environment.apiUrl}${apiLists.booking_reschedule}${bookingId}/reschedule/${proposal.id}/${action}/`,
      {}
    ).subscribe({
      next: () => {
        this.toastr.success(`Reschedule proposal ${accept ? 'accepted' : 'rejected'}.`);
        this.getBookings();
      },
      error: (error) => this.toastr.error(error?.error?.detail || 'Unable to respond to the proposal.')
    });
  }

  cancelBooking(item: any): void {
    const bookingId = this.bookingId(item);
    if (!bookingId) {
      return;
    }

    const dialogRef = this.dialog.open(CancelBookingComponent, {
      width: '560px',
      maxWidth: 'calc(100vw - 32px)',
      panelClass: 'profile-drawer',
      data: { bookingId }
    });

    dialogRef.closed.subscribe((result: any) => {
      if (result?.cancelled) {
        this.getBookings();
      }
    });
  }

  bookService(): void {
    this.route.navigateByUrl('student/dashboard');
  }
}

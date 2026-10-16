import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { apiLists } from '../../resources/apiLists';

@Component({
  selector: 'app-service-dashboard',
  templateUrl: './service-dashboard.component.html',
  styleUrls: ['./service-dashboard.component.scss']
})
export class ServiceDashboardComponent implements OnInit {
  service: any = history.state?.service || null;
  reviews: any[] = [];
  enrolledStudents: any[] = [];
  enrolledLoading = true;
  loading = !this.service;
  reviewsLoading = true;
  errorMessage = '';
  currentMediaIndex = 0;
  private serviceKey = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.serviceKey = this.route.snapshot.paramMap.get('serviceId') || '';
    if (!this.service) {
      this.loadServiceFromDashboard();
    } else {
      this.loadReviews();
      this.loadEnrolledStudents();
    }
  }

  /**
   * Accepted bookings are the enrolment records for this service.
   *
   * The count that used to be shown came from whichever object the caller put
   * in router state; a service payload carries no enrolment data, so it always
   * read as zero. Ask the bookings endpoint directly instead, which also gives
   * us the students themselves rather than just a number.
   */
  private loadEnrolledStudents(): void {
    const serviceId =
      this.service?.service?.id || this.service?.service_id || this.service?.id;
    if (!serviceId) {
      this.enrolledLoading = false;
      return;
    }
    const params = new URLSearchParams();
    params.set('service_id', serviceId);
    params.set('status', 'ACCEPTED');
    this.http
      .get<any>(environment.apiUrl + apiLists.get_booked_services + '?' + params)
      .subscribe({
        next: response => {
          this.enrolledStudents = response?.data || [];
          this.enrolledLoading = false;
        },
        error: () => {
          this.enrolledStudents = [];
          this.enrolledLoading = false;
        }
      });
  }

  studentName(booking: any): string {
    return booking?.student?.user?.full_name || 'Student';
  }

  studentPicture(booking: any): string | null {
    return booking?.student?.profile_picture_url || null;
  }

  goBack(): void {
    this.router.navigate(['/tutor/dashboard']);
  }

  serviceDate(): Date | null {
    if (!this.service?.date) {
      return null;
    }
    const date = new Date(`${this.service.date}T${this.service.time || '00:00:00'}`);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  timeRange(): string {
    const start = this.service?.time?.slice(0, 5) || '--:--';
    const end = this.service?.end_time?.slice(0, 5);
    return end ? `${start} - ${end}` : start;
  }

  serviceMedia(): Array<{ type: 'image' | 'video'; url: string }> {
    const service = this.service?.service || this.service;
    if (!service) {
      return [];
    }

    const imageUrls = Array.isArray(service.image_urls)
      ? service.image_urls.filter((url: string | null | undefined) => !!url)
      : [];
    const videoUrls = Array.isArray(service.video_urls)
      ? service.video_urls.filter((url: string | null | undefined) => !!url)
      : [];
    const singleVideoUrl = service.video_url ? [service.video_url] : [];
    const allVideoUrls = [...videoUrls, ...singleVideoUrl.filter((url: string) => !videoUrls.includes(url))];

    return [
      ...imageUrls.map((url: string) => ({ type: 'image' as const, url })),
      ...allVideoUrls.map((url: string) => ({ type: 'video' as const, url }))
    ];
  }

  currentMedia(): { type: 'image' | 'video'; url: string } | null {
    const media = this.serviceMedia();
    return media.length ? media[this.currentMediaIndex % media.length] : null;
  }

  setMedia(index: number): void {
    const media = this.serviceMedia();
    if (media.length) {
      this.currentMediaIndex = ((index % media.length) + media.length) % media.length;
    }
  }

  moveMedia(direction: number): void {
    this.setMedia(this.currentMediaIndex + direction);
  }

  reviewAverage(): string {
    if (!this.reviews.length) {
      return '0.0';
    }
    const total = this.reviews.reduce((sum, review) => sum + Number(review.rating || 0), 0);
    return (total / this.reviews.length).toFixed(1);
  }

  reviewStars(rating: number): number[] {
    return Array.from({ length: 5 }, (_, index) => index < rating ? 1 : 0);
  }

  initials(name: string): string {
    return (name || 'Student')
      .split(' ')
      .map(part => part.charAt(0))
      .join('')
      .slice(0, 2)
      .toUpperCase();
  }

  private loadServiceFromDashboard(): void {
    this.http.get<any>(environment.apiUrl + apiLists.dashboard_tutor).subscribe({
      next: response => {
        const services = response?.data?.upcoming_services || [];
        this.service = services.find((item: any) => this.serviceIdentifier(item) === this.serviceKey);
        this.loading = false;
        if (this.service) {
          this.loadReviews();
          this.loadEnrolledStudents();
        } else {
          this.enrolledLoading = false;
          this.errorMessage = 'This service could not be found.';
        }
      },
      error: () => {
        this.loading = false;
        this.enrolledLoading = false;
        this.errorMessage = 'Unable to load this service right now.';
      }
    });
  }

  private loadReviews(): void {
    const serviceId = this.service?.service?.id || this.service?.service_id || this.service?.id;
    if (!serviceId) {
      this.reviewsLoading = false;
      return;
    }

    const params = new URLSearchParams();
    params.set('service_id', serviceId);
    this.http.get<any>(environment.apiUrl + apiLists.service_review + '?' + params).subscribe({
      next: response => {
        this.reviews = response?.data || [];
        this.reviewsLoading = false;
      },
      error: () => this.reviewsLoading = false
    });
  }

  private serviceIdentifier(service: any): string {
    return String(service?.id || service?.service_id || service?.booking_id || '');
  }
}

import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { Dialog } from '@angular/cdk/dialog';
import { environment } from '../../../environments/environment';
import { apiLists } from '../../resources/apiLists';
import { ServiceCardComponent } from '../../resources/Modals/service-card/service-card.component';

@Component({
  selector: 'app-service-details',
  templateUrl: './service-details.component.html',
  styleUrls: ['./service-details.component.scss']
})
export class ServiceDetailsComponent implements OnInit {
  service: any = history.state?.service || null;
  loading = !this.service;
  currentMediaIndex = 0;
  tutorId = localStorage.getItem('tutor_id') || '';
  reviews: any[] = [];
  reviewsLoading = true;
  enrolledStudents: any[] = [];
  enrolledLoading = true;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private http: HttpClient,
    private dialog: Dialog
  ) {}

  ngOnInit(): void {
    if (!this.service) {
      this.loadService();
    } else {
      this.loadReviews();
      this.loadEnrolledStudents();
    }
  }

  /**
   * Accepted bookings are this service's enrolment records.
   *
   * The service payload carries no enrolment data, so the count rendered here
   * was always undefined; fetch the bookings instead so the panel can list the
   * students as well as count them.
   */
  private loadEnrolledStudents(): void {
    const serviceId = this.service?.id;
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

  goBack(): void { this.router.navigate(['/tutor/services']); }

  loadService(): void {
    const params = new URLSearchParams();
    params.set('tutor_id', this.tutorId);
    this.http.get<any>(environment.apiUrl + apiLists.servicelist + '?' + params).subscribe({
      next: response => {
        const serviceId = this.route.snapshot.paramMap.get('serviceId');
        this.service = (response?.data || []).find((item: any) => String(item.id) === serviceId);
        this.loading = false;
        if (this.service) {
          this.loadReviews();
          this.loadEnrolledStudents();
        } else {
          this.enrolledLoading = false;
        }
      },
      error: () => {
        this.loading = false;
        this.enrolledLoading = false;
      }
    });
  }

  editService(): void {
    const dialogRef = this.dialog.open(ServiceCardComponent, {
      panelClass: ['profile-drawer'],
      data: { tutor_id: this.tutorId, item: this.service }
    });
    dialogRef.closed.subscribe(() => this.loadService());
  }

  media(): Array<{ type: 'image' | 'video'; url: string }> {
    const images = Array.isArray(this.service?.image_urls) ? this.service.image_urls : [];
    const videos = Array.isArray(this.service?.video_urls) ? this.service.video_urls : [];
    const singleVideo = this.service?.video_url && !videos.includes(this.service.video_url) ? [this.service.video_url] : [];
    return [
      ...images.filter(Boolean).map((url: string) => ({ type: 'image' as const, url })),
      ...[...videos, ...singleVideo].filter(Boolean).map((url: string) => ({ type: 'video' as const, url }))
    ];
  }

  currentMedia(): { type: 'image' | 'video'; url: string } | null {
    const media = this.media();
    return media.length ? media[this.currentMediaIndex % media.length] : null;
  }

  setMedia(index: number): void {
    const media = this.media();
    if (media.length) this.currentMediaIndex = ((index % media.length) + media.length) % media.length;
  }

  moveMedia(direction: number): void { this.setMedia(this.currentMediaIndex + direction); }

  reviewAverage(): string {
    if (!this.reviews.length) return '0.0';
    const total = this.reviews.reduce((sum, review) => sum + Number(review.rating || 0), 0);
    return (total / this.reviews.length).toFixed(1);
  }

  reviewStars(rating: number): number[] {
    return Array.from({ length: 5 }, (_, index) => index < rating ? 1 : 0);
  }

  initials(name: string): string {
    return (name || 'Student').split(' ').map(part => part.charAt(0)).join('').slice(0, 2).toUpperCase();
  }

  private loadReviews(): void {
    const serviceId = this.service?.id || this.service?.service_id;
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
}

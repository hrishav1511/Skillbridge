import { HttpClient } from '@angular/common/http';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { environment } from '../../../environments/environment';
import { apiLists } from '../../resources/apiLists';
import { PaymentStep } from '../../resources/models';

@Component({
  selector: 'app-payment-portal',
  templateUrl: './payment-portal.component.html',
  styleUrls: ['./payment-portal.component.scss']
})
export class PaymentPortalComponent implements OnInit, OnDestroy {

  step: PaymentStep = 'review';
  service: any = null;
  serviceId = '';
  bookingErrorMessage = 'We could not confirm your booking. Please try again.';
  private bookingTimer?: ReturnType<typeof setTimeout>;

  constructor(private route: ActivatedRoute, private router: Router, private http: HttpClient, private toastr: ToastrService) {}

  ngOnInit(): void {
    this.serviceId = this.route.snapshot.paramMap.get('id') || '';
    this.service = history.state?.service || null;
  }

  ngOnDestroy(): void {
    if (this.bookingTimer) {
      clearTimeout(this.bookingTimer);
    }
  }

  get payableAmount(): number {
    return Number(this.service?.price || 0);
  }

  get serviceInitials(): string {
    const name = this.service?.tutor?.full_name || 'SkillBridge';
    return name.split(' ').map((part: string) => part.charAt(0)).slice(0, 2).join('').toUpperCase();
  }

  /**
   * Confirming goes straight to the booking call. There is no card-details
   * step: the confirmation animation covers the request, then the student
   * lands on the success or error card as before.
   */
  confirmBooking(): void {
    if (this.step === 'processing') {
      return;
    }

    this.step = 'processing';
    window.scrollTo({ top: 0, behavior: 'smooth' });

    this.bookingTimer = setTimeout(() => {
      // The student is resolved from the access token server-side; sending a
      // client-held student_id only risks a mismatch.
      const payload = {
        service_id: this.service?.id || this.serviceId
      };

      this.http.post<any>(`${environment.apiUrl}${apiLists.service_booking}`, payload).subscribe({
        next: () => {
          this.step = 'success';
        },
        error: (error) => {
          this.bookingErrorMessage = error?.error?.detail || this.bookingErrorMessage;
          this.step = 'error';
        }
      });
    }, 3000);
  }

  goToServices(): void {
    this.router.navigate(['/student/booked-services']);
  }

  retryBooking(): void {
    this.step = 'review';
    this.bookingErrorMessage = 'We could not confirm your booking. Please try again.';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  returnToDashboard(): void {
    this.router.navigate(['/student/dashboard']);
  }
}

import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Dialog } from '@angular/cdk/dialog';
import { ToastrService } from 'ngx-toastr';
import { environment } from '../../../environments/environment';
import { apiLists } from '../../resources/apiLists';
import {
  RescheduleDialogComponent,
  RescheduleDialogResult
} from '../../resources/Modals/reschedule-dialog/reschedule-dialog.component';

/**
 * The full list of service requests for a tutor.
 *
 * The dashboard panel only shows the most recent few; this page pages through
 * all of them and can be narrowed by status. Both the paging and the status
 * filter are applied server-side.
 */
@Component({
  selector: 'app-service-requests',
  templateUrl: './service-requests.component.html',
  styleUrls: ['./service-requests.component.scss']
})
export class ServiceRequestsComponent implements OnInit {
  requests: any[] = [];
  loading = true;
  error = '';

  selectedStatus = '';
  page = 1;
  totalPages = 1;
  totalRecords = 0;
  readonly itemsPerPage = 10;
  readonly statusOptions = [
    { value: '', label: 'All statuses' },
    { value: 'PENDING', label: 'Pending' },
    { value: 'ACCEPTED', label: 'Accepted' },
    { value: 'DECLINED', label: 'Declined' },
    { value: 'CANCELLED', label: 'Cancelled' }
  ];

  currentUserId: string | null = JSON.parse(localStorage.getItem('user_id') || 'null');

  constructor(
    private http: HttpClient,
    private router: Router,
    private dialog: Dialog,
    private toastr: ToastrService
  ) {}

  ngOnInit(): void {
    this.getRequests();
  }

  goBack(): void {
    this.router.navigate(['/tutor/dashboard']);
  }

  getRequests(): void {
    this.loading = true;
    this.error = '';

    const params = new URLSearchParams();
    params.set('page', String(this.page));
    params.set('items_per_page', String(this.itemsPerPage));
    if (this.selectedStatus) {
      params.set('status', this.selectedStatus);
    }

    this.http.get<any>(environment.apiUrl + apiLists.get_booked_services + '?' + params)
      .subscribe({
        next: response => {
          this.requests = response?.data || [];
          const metadata = response?.metadata || {};
          this.totalPages = Number(metadata.total_page) || 1;
          this.totalRecords = Number(metadata.total_records) || 0;
          this.page = Number(metadata.current_page) || this.page;
          this.loading = false;
        },
        error: error => {
          this.error = error?.error?.message || 'Unable to load service requests.';
          this.requests = [];
          this.loading = false;
        }
      });
  }

  onStatusChange(status: string): void {
    this.selectedStatus = status;
    this.page = 1;
    this.getRequests();
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages || page === this.page) {
      return;
    }
    this.page = page;
    this.getRequests();
  }

  bookingStatus(booking: any): string {
    return String(booking?.status || booking?.booking_status || 'PENDING').toUpperCase();
  }

  pendingProposal(booking: any): any | null {
    return (booking?.reschedule_proposals || [])
      .find((proposal: any) => proposal.proposal_status === 'PENDING') || null;
  }

  updateBooking(booking: any, action: 'accept' | 'decline'): void {
    this.http.patch(
      `${environment.apiUrl}${apiLists.cancel_booking}${booking.id}/${action}/`,
      {}
    ).subscribe({
      next: () => {
        this.toastr.success(`Service request ${action === 'accept' ? 'accepted' : 'declined'}.`);
        this.getRequests();
      },
      error: (error) => this.toastr.error(error?.error?.detail || 'Unable to update this request.')
    });
  }

  cancelService(booking: any): void {
    this.http.delete(
      `${environment.apiUrl}${apiLists.cancel_booking}${booking.id}/`,
      { body: {} }
    ).subscribe({
      next: () => {
        this.toastr.success('Service cancelled.');
        this.getRequests();
      },
      error: (error) => this.toastr.error(error?.error?.detail || 'Unable to cancel this service.')
    });
  }

  proposeReschedule(booking: any): void {
    const dialogRef = this.dialog.open<RescheduleDialogResult>(RescheduleDialogComponent, {
      panelClass: ['profile-drawer'],
      data: {
        currentStartAt: booking?.scheduled_start_at,
        serviceName: booking?.service?.service_name
      }
    });

    dialogRef.closed.subscribe((result) => {
      if (!result?.proposedStartAt) {
        return;
      }
      this.http.post(
        `${environment.apiUrl}${apiLists.booking_reschedule}${booking.id}/reschedule/`,
        { proposed_start_at: result.proposedStartAt }
      ).subscribe({
        next: () => {
          this.toastr.success('Reschedule proposal sent.');
          this.getRequests();
        },
        error: (error) => this.toastr.error(error?.error?.detail || 'Unable to propose a new time.')
      });
    });
  }

  respondToProposal(booking: any, accept: boolean): void {
    const proposal = this.pendingProposal(booking);
    if (!proposal?.id) {
      return;
    }
    const action = accept ? 'accept' : 'reject';
    this.http.patch(
      `${environment.apiUrl}${apiLists.booking_reschedule}${booking.id}/reschedule/${proposal.id}/${action}/`,
      {}
    ).subscribe({
      next: () => {
        this.toastr.success(`Reschedule proposal ${accept ? 'accepted' : 'rejected'}.`);
        this.getRequests();
      },
      error: (error) => this.toastr.error(error?.error?.detail || 'Unable to respond to this proposal.')
    });
  }

  canRespondToProposal(booking: any): boolean {
    const proposal = this.pendingProposal(booking);
    return !!proposal && proposal.proposed_by_user_id !== this.currentUserId;
  }
}

import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { HttpClient } from '@angular/common/http';
import { Component, Inject } from '@angular/core';
import { ToastrService } from 'ngx-toastr';
import { environment } from '../../../../environments/environment';
import { apiLists } from '../../apiLists';

@Component({
  selector: 'app-cancel-booking',
  templateUrl: './cancel-booking.component.html',
  styleUrls: ['./cancel-booking.component.scss']
})
export class CancelBookingComponent {
  reason = '';
  cancelling = false;

  constructor(
    @Inject(DIALOG_DATA) public data: { bookingId: string },
    private dialogRef: DialogRef<{ cancelled: boolean }>,
    private http: HttpClient,
    private toastr: ToastrService
  ) {}

  close(): void {
    if (!this.cancelling) {
      this.dialogRef.close();
    }
  }

  confirmCancellation(): void {
    if (!this.data?.bookingId || this.cancelling) {
      return;
    }

    this.cancelling = true;
    this.http.delete(
      `${environment.apiUrl}${apiLists.cancel_booking}${this.data.bookingId}/`,
      { body: { reason: this.reason.trim() } }
    ).subscribe({
      next: () => {
        this.toastr.success('Booking cancelled successfully.');
        this.dialogRef.close({ cancelled: true });
      },
      error: (error) => {
        this.cancelling = false;
        this.toastr.error(error?.error?.detail || 'Unable to cancel this booking.');
      }
    });
  }
}

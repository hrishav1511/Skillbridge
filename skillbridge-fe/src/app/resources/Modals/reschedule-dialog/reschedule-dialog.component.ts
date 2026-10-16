import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { Component, Inject } from '@angular/core';

export interface RescheduleDialogData {
  /** Current service time, used to prefill the inputs. */
  currentStartAt?: string | null;
  /** Service name, shown so the user knows what they are moving. */
  serviceName?: string | null;
}

export interface RescheduleDialogResult {
  /** The proposed start, as an ISO-8601 string. */
  proposedStartAt: string;
}

/**
 * In-app replacement for the `window.prompt` that asked for a new service time
 * as free text in "YYYY-MM-DDTHH:mm" format.
 *
 * Typing a datetime into a prompt is easy to get wrong and was validated only
 * after the prompt closed, so a typo lost the entry entirely. Separate date and
 * time inputs cannot produce a malformed value, and the past-date check runs
 * inline while the dialog is still open.
 */
@Component({
  selector: 'app-reschedule-dialog',
  templateUrl: './reschedule-dialog.component.html',
  styleUrls: ['./reschedule-dialog.component.scss']
})
export class RescheduleDialogComponent {
  date = '';
  time = '';
  touched = false;
  readonly minDate = new Date().toISOString().slice(0, 10);

  constructor(
    @Inject(DIALOG_DATA) public data: RescheduleDialogData,
    private dialogRef: DialogRef<RescheduleDialogResult>
  ) {
    const current = this.data?.currentStartAt ? new Date(this.data.currentStartAt) : null;
    if (current && !Number.isNaN(current.getTime())) {
      this.date = this.toDateInput(current);
      this.time = this.toTimeInput(current);
    }
  }

  /** The chosen moment, or null when the inputs are incomplete or invalid. */
  get proposed(): Date | null {
    if (!this.date || !this.time) {
      return null;
    }
    const parsed = new Date(`${this.date}T${this.time}`);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  get isPast(): boolean {
    const proposed = this.proposed;
    return !!proposed && proposed.getTime() <= Date.now();
  }

  get isValid(): boolean {
    return !!this.proposed && !this.isPast;
  }

  close(): void {
    this.dialogRef.close();
  }

  confirm(): void {
    this.touched = true;
    const proposed = this.proposed;
    if (!proposed || this.isPast) {
      return;
    }
    this.dialogRef.close({ proposedStartAt: proposed.toISOString() });
  }

  /** Local date parts, so the prefill matches what the user sees, not UTC. */
  private toDateInput(value: Date): string {
    const month = String(value.getMonth() + 1).padStart(2, '0');
    const day = String(value.getDate()).padStart(2, '0');
    return `${value.getFullYear()}-${month}-${day}`;
  }

  private toTimeInput(value: Date): string {
    const hours = String(value.getHours()).padStart(2, '0');
    const minutes = String(value.getMinutes()).padStart(2, '0');
    return `${hours}:${minutes}`;
  }
}

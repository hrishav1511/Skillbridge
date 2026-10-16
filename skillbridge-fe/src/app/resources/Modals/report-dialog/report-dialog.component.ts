import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { HttpClient } from '@angular/common/http';
import { Component, Inject } from '@angular/core';
import { ToastrService } from 'ngx-toastr';
import { environment } from '../../../../environments/environment';

export interface ReportDialogData {
  /** API path to post the report to, e.g. apiLists.report_tutor. */
  endpoint: string;
  /** Identifier fields for the reported entity, e.g. { tutor_id: '...' }. */
  target: Record<string, string>;
  /** What is being reported, used in the copy: 'Tutor', 'Service', 'Review'. */
  label: string;
  /** Optional name of the entity, shown so the user knows what they are reporting. */
  entityName?: string | null;
}

/**
 * In-app replacement for the `window.prompt` that used to collect a report
 * reason. Native dialogs cannot be styled, are blocked by some browsers and
 * gave no inline validation - the reason was checked only after the prompt had
 * already closed, so a too-short reason lost whatever the user had typed.
 */
@Component({
  selector: 'app-report-dialog',
  templateUrl: './report-dialog.component.html',
  styleUrls: ['./report-dialog.component.scss']
})
export class ReportDialogComponent {
  readonly minLength = 10;
  readonly maxLength = 1000;

  reason = '';
  submitting = false;
  touched = false;
  serverError = '';

  constructor(
    @Inject(DIALOG_DATA) public data: ReportDialogData,
    private dialogRef: DialogRef<{ reported: boolean }>,
    private http: HttpClient,
    private toastr: ToastrService
  ) {}

  get trimmedLength(): number {
    return this.reason.trim().length;
  }

  get isTooShort(): boolean {
    return this.trimmedLength < this.minLength;
  }

  get lowercaseLabel(): string {
    return (this.data?.label || 'item').toLowerCase();
  }

  close(): void {
    if (!this.submitting) {
      this.dialogRef.close();
    }
  }

  submit(): void {
    this.touched = true;
    this.serverError = '';
    if (this.isTooShort || this.submitting) {
      return;
    }

    this.submitting = true;
    this.http.post(environment.apiUrl + this.data.endpoint, {
      ...this.data.target,
      reason: this.reason.trim()
    }).subscribe({
      next: () => {
        this.toastr.success(
          `${this.data.label} report submitted for administrator review.`
        );
        this.dialogRef.close({ reported: true });
      },
      error: (error) => {
        this.submitting = false;
        // Keep the typed reason on screen and say why it was refused, rather
        // than closing and dropping it.
        const detail = error?.error?.detail;
        this.serverError =
          (Array.isArray(detail) ? detail[0]?.message : detail) ||
          error?.error?.message ||
          `Unable to report this ${this.lowercaseLabel}.`;
      }
    });
  }
}

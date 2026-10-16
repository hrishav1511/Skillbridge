import { Dialog } from '@angular/cdk/dialog';
import { HttpClient } from '@angular/common/http';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { environment } from 'src/environments/environment';
import { apilists } from '../../resources/ApiList';
import {
  RecordDialogComponent,
  RecordDialogResult
} from '../record-dialog/record-dialog.component';

interface TutorReport {
  id: string;
  student_id: string;
  tutor_id: string;
  reason: string;
  reporter_name?: string | null;
  tutor_name?: string | null;
  tutor_profile_picture_url?: string | null;
  reported_at?: string | null;
}

interface ServiceReport {
  id: string;
  student_id: string;
  service_id: string;
  reason: string;
  reporter_name?: string | null;
  service_name?: string | null;
  reported_at?: string | null;
}

interface ReviewReport {
  id: string;
  reporter_user_id: string;
  review_type: 'tutor' | 'service';
  review_id: string;
  reason: string;
  review_comment?: string | null;
  review_rating?: number | null;
  reporter_name?: string | null;
  reported_at?: string | null;
}

export type ReportTab = 'tutor' | 'service' | 'review';

/** Both of these delete the report; they differ only in what the admin means. */
type DeleteReason = 'discard' | 'resolved';

interface PendingAction {
  tab: ReportTab;
  reportId: string;
  reason: DeleteReason;
  entityName: string;
}

const TABS: ReportTab[] = ['tutor', 'service', 'review'];

/**
 * Moderation queues for reported tutors, services and reviews.
 *
 * Every row offers Open (inspect the reported record), Discard and Resolved.
 * The last two both delete the report and cannot be undone from the panel, so
 * each is held behind a confirmation rather than firing on the first click.
 */
@Component({
  selector: 'app-reports',
  templateUrl: './reports.component.html',
  styleUrls: ['./reports.component.scss']
})
export class ReportsComponent implements OnInit, OnDestroy {
  activeTab: ReportTab = 'tutor';
  tutorReports: TutorReport[] = [];
  serviceReports: ServiceReport[] = [];
  reviewReports: ReviewReport[] = [];
  loading = true;
  error = '';
  notice = '';

  pendingAction: PendingAction | null = null;
  submitting = false;

  private queryParamSubscription?: Subscription;

  constructor(
    private http: HttpClient,
    private dialog: Dialog,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    /*
     * The dashboard links here with ?tab=<queue>, so the admin lands on the
     * table they clicked Manage from instead of always on Reported Tutors.
     */
    this.queryParamSubscription = this.route.queryParamMap.subscribe(params => {
      const requested = (params.get('tab') || '').toLowerCase() as ReportTab;
      this.activeTab = TABS.includes(requested) ? requested : 'tutor';
    });
    this.getReports();
  }

  ngOnDestroy(): void {
    this.queryParamSubscription?.unsubscribe();
  }

  selectTab(tab: ReportTab): void {
    this.activeTab = tab;
    this.notice = '';
    // Keep the URL shareable and the back button meaningful.
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { tab },
      replaceUrl: true
    });
  }

  getReports(): void {
    this.loading = true;
    this.error = '';

    this.http.get<{ data: TutorReport[] }>(environment.apiUrl + apilists.tutor_reports)
      .subscribe({
        next: response => {
          this.tutorReports = response.data || [];
          this.loading = false;
        },
        error: () => {
          this.error = 'Unable to load reported tutors.';
          this.loading = false;
        }
      });

    this.http.get<{ data: ServiceReport[] }>(environment.apiUrl + apilists.service_reports)
      .subscribe({
        next: response => this.serviceReports = response.data || [],
        error: () => this.error = 'Unable to load reported services.'
      });

    this.http.get<{ data: ReviewReport[] }>(environment.apiUrl + apilists.review_reports)
      .subscribe({
        next: response => this.reviewReports = response.data || [],
        error: () => this.error = 'Unable to load reported reviews.'
      });
  }

  // ---------------------------------------------------------------- Open ---

  /**
   * Show the reported record.
   *
   * The report row carries only a summary, so the tutor and service records
   * are fetched fresh; a review report already carries the review itself.
   */
  openReport(tab: ReportTab, report: any): void {
    this.error = '';

    if (tab === 'review') {
      this.showRecord('review', report, false);
      return;
    }

    if (tab === 'tutor') {
      this.http.get<{ data: any[] }>(
        `${environment.apiUrl}tutor/tutors/?tutor_id=${report.tutor_id}`
      ).subscribe({
        next: response => this.showRecord(
          'tutor',
          response.data?.[0] || { ...report, id: report.tutor_id },
          true
        ),
        error: () => this.showRecord('tutor', { ...report, id: report.tutor_id }, true)
      });
      return;
    }

    this.http.get<{ data: any[] }>(
      `${environment.apiUrl}service/services/?service_id=${report.service_id}`
    ).subscribe({
      next: response => this.showRecord(
        'service',
        response.data?.[0] || { ...report, id: report.service_id },
        true
      ),
      error: () => this.showRecord('service', { ...report, id: report.service_id }, true)
    });
  }

  private showRecord(kind: ReportTab, record: any, allowStatusChange: boolean): void {
    this.dialog.open<RecordDialogResult | undefined>(RecordDialogComponent, {
      data: { kind, record, allowStatusChange }
    }).closed.subscribe(result => {
      if (!result) {
        return;
      }
      this.applyStatusChange(kind, result);
    });
  }

  private applyStatusChange(kind: ReportTab, result: RecordDialogResult): void {
    const status = result.action === 'disable' ? 'INACTIVE' : 'ACTIVE';
    const id = result.record?.id;
    if (!id) {
      return;
    }

    const url = kind === 'tutor'
      ? `${environment.apiUrl}admin/tutors/${id}/status/`
      : `${environment.apiUrl}admin/services/${id}/status/`;

    this.http.patch(url, { status }).subscribe({
      next: () => {
        this.notice = status === 'INACTIVE'
          ? `That ${kind} was disabled and is no longer shown to students.`
          : `That ${kind} was re-enabled.`;
        this.getReports();
      },
      error: error => this.error = this.messageFor(error, 'That change could not be saved.')
    });
  }

  // ------------------------------------------------- Discard / Resolved ---

  /** Stage a deletion; nothing is sent until confirmAction() runs. */
  askToDelete(tab: ReportTab, reportId: string, reason: DeleteReason, entityName: string): void {
    this.pendingAction = { tab, reportId, reason, entityName };
  }

  cancelAction(): void {
    if (!this.submitting) {
      this.pendingAction = null;
    }
  }

  get confirmTitle(): string {
    if (!this.pendingAction) {
      return '';
    }
    return this.pendingAction.reason === 'discard'
      ? 'Discard this report?'
      : 'Mark this report resolved?';
  }

  get confirmMessage(): string {
    if (!this.pendingAction) {
      return '';
    }
    const name = this.pendingAction.entityName;
    return this.pendingAction.reason === 'discard'
      ? `The report against ${name} will be deleted without further action. This cannot be undone.`
      : `The report against ${name} will be deleted because it has been dealt with. This cannot be undone.`;
  }

  confirmAction(): void {
    const action = this.pendingAction;
    if (!action || this.submitting) {
      return;
    }

    this.submitting = true;
    const base = this.endpointFor(action.tab);

    this.http.delete(`${environment.apiUrl}${base}${action.reportId}/`).subscribe({
      next: () => {
        this.notice = action.reason === 'discard'
          ? `The report against ${action.entityName} was discarded.`
          : `The report against ${action.entityName} was marked resolved.`;
        this.submitting = false;
        this.pendingAction = null;
        this.getReports();
      },
      error: error => {
        this.submitting = false;
        this.pendingAction = null;
        this.error = this.messageFor(error, 'That action could not be completed.');
      }
    });
  }

  private endpointFor(tab: ReportTab): string {
    if (tab === 'tutor') {
      return apilists.tutor_reports;
    }
    return tab === 'service' ? apilists.service_reports : apilists.review_reports;
  }

  private messageFor(error: any, fallback: string): string {
    return error?.error?.detail || error?.error?.message || fallback;
  }
}

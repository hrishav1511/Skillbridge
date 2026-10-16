import { Dialog } from '@angular/cdk/dialog';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { environment } from 'src/environments/environment';
import {
  RecordDialogComponent,
  RecordDialogResult
} from '../record-dialog/record-dialog.component';

interface AdminTutor {
  id: string;
  academic_program?: string | null;
  bio?: string | null;
  teaching_style?: string | null;
  phone?: string | null;
  is_visible?: boolean;
  accepting_requests?: boolean;
  account_status?: string;
  approval_status?: string | null;
  average_rating?: string | null;
  tags?: string[] | null;
  profile_picture_url?: string | null;
  user?: { full_name?: string; email?: string; phone?: string } | null;
}

/**
 * Every tutor, with the full record behind a row click.
 *
 * Tutor Visibility already shows the visibility/requests state; this page is
 * the record list the moderation spec asks for, so a report can be traced to
 * the whole account rather than a single column.
 */
@Component({
  selector: 'app-tutors-list',
  templateUrl: './tutors-list.component.html',
  styleUrls: ['../services-list/services-list.component.scss']
})
export class TutorsListComponent implements OnInit {
  tutors: AdminTutor[] = [];
  loading = true;
  error = '';
  notice = '';
  search = '';

  constructor(private http: HttpClient, private dialog: Dialog) {}

  ngOnInit(): void {
    this.getTutors();
  }

  get visibleTutors(): AdminTutor[] {
    const term = this.search.trim().toLowerCase();
    if (!term) {
      return this.tutors;
    }
    return this.tutors.filter(tutor =>
      (tutor.user?.full_name || '').toLowerCase().includes(term) ||
      (tutor.user?.email || '').toLowerCase().includes(term) ||
      (tutor.academic_program || '').toLowerCase().includes(term)
    );
  }

  getTutors(): void {
    this.loading = true;
    this.error = '';
    this.http.get<{ data: AdminTutor[] }>(`${environment.apiUrl}admin/tutors/`)
      .subscribe({
        next: response => {
          this.tutors = response.data || [];
          this.loading = false;
        },
        error: () => {
          this.error = 'Unable to load tutors.';
          this.loading = false;
        }
      });
  }

  isDisabled(tutor: AdminTutor): boolean {
    return String(tutor.account_status || 'ACTIVE').toUpperCase() === 'INACTIVE';
  }

  openTutor(tutor: AdminTutor): void {
    this.notice = '';
    this.dialog.open<RecordDialogResult | undefined>(RecordDialogComponent, {
      data: { kind: 'tutor', record: tutor, allowStatusChange: true }
    }).closed.subscribe(result => {
      if (result) {
        this.setStatus(tutor, result.action === 'disable' ? 'INACTIVE' : 'ACTIVE');
      }
    });
  }

  setStatus(tutor: AdminTutor, status: 'ACTIVE' | 'INACTIVE'): void {
    this.http.patch(
      `${environment.apiUrl}admin/tutors/${tutor.id}/status/`,
      { status }
    ).subscribe({
      next: () => {
        tutor.account_status = status;
        const name = tutor.user?.full_name || 'That tutor';
        this.notice = status === 'INACTIVE'
          ? `${name} was deactivated.`
          : `${name} was reactivated.`;
      },
      error: error => {
        this.error = error?.error?.detail || 'That tutor could not be updated.';
      }
    });
  }
}

import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { apilists } from 'src/app/resources/ApiList';
import { environment } from 'src/environments/environment';

interface TutorVisibilityRecord {
  id: string;
  academic_program?: string;
  is_visible?: boolean;
  account_status?: string;
  accepting_requests?: boolean;
  user?: {
    full_name?: string;
    email?: string;
  };
}

@Component({
  selector: 'app-tutor-visibility',
  templateUrl: './tutor-visibility.component.html',
  styleUrls: ['./tutor-visibility.component.scss']
})
export class TutorVisibilityComponent implements OnInit {
  tutors: TutorVisibilityRecord[] = [];
  busyTutorId: string | null = null;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.getTutors();
  }

  private getTutors(): void {
    const apiRoot = environment.apiUrl.replace(/v1\/$/, '');
    const endpoint = apilists.tutor_visibility.replace(/^\//, '');

    this.http.get<{ data: TutorVisibilityRecord[] }>(apiRoot + endpoint).subscribe({
      next: (response) => {
        this.tutors = response.data || [];
      }
    });
  }

  getStatusClass(status: string | undefined): string {
    return (status || 'unknown').toLowerCase().replace(/\s+/g, '-');
  }

  setAccountStatus(tutor: TutorVisibilityRecord, status: 'ACTIVE' | 'INACTIVE'): void {
    this.busyTutorId = tutor.id;
    this.http.patch(
      `${environment.apiUrl}admin/tutors/${tutor.id}/status/`,
      { status }
    ).subscribe({
      next: () => {
        /*
         * Deactivation is its own state on the tutor record - it does not
         * rewrite the tutor's own visibility or availability settings, so the
         * table must not pretend it did.
         */
        tutor.account_status = status;
        this.busyTutorId = null;
      },
      error: () => { this.busyTutorId = null; }
    });
  }
}

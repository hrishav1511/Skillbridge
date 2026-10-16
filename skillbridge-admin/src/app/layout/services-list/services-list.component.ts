import { Dialog } from '@angular/cdk/dialog';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { environment } from 'src/environments/environment';
import { apilists } from '../../resources/ApiList';
import {
  RecordDialogComponent,
  RecordDialogResult
} from '../record-dialog/record-dialog.component';

interface AdminService {
  id: string;
  service_name: string;
  description?: string | null;
  date?: string | null;
  time?: string | null;
  end_time?: string | null;
  price?: number;
  level?: string;
  status?: string;
  approval_status?: string | null;
  image_urls?: string[] | null;
  video_urls?: string[] | null;
  video_url?: string | null;
  tags?: string[] | null;
  tutor?: { full_name?: string; email?: string } | null;
}

/**
 * Every service, disabled ones included, with the full record behind a row
 * click. Disabling here hides the service from students.
 */
@Component({
  selector: 'app-services-list',
  templateUrl: './services-list.component.html',
  styleUrls: ['./services-list.component.scss']
})
export class ServicesListComponent implements OnInit {
  services: AdminService[] = [];
  loading = true;
  error = '';
  notice = '';
  search = '';

  constructor(private http: HttpClient, private dialog: Dialog) {}

  ngOnInit(): void {
    this.getServices();
  }

  get visibleServices(): AdminService[] {
    const term = this.search.trim().toLowerCase();
    if (!term) {
      return this.services;
    }
    return this.services.filter(service =>
      (service.service_name || '').toLowerCase().includes(term) ||
      (service.tutor?.full_name || '').toLowerCase().includes(term)
    );
  }

  getServices(): void {
    this.loading = true;
    this.error = '';
    this.http.get<{ data: AdminService[] }>(environment.apiUrl + apilists.admin_services)
      .subscribe({
        next: response => {
          this.services = response.data || [];
          this.loading = false;
        },
        error: () => {
          this.error = 'Unable to load services.';
          this.loading = false;
        }
      });
  }

  isDisabled(service: AdminService): boolean {
    return String(service.status || 'ACTIVE').toUpperCase() === 'INACTIVE';
  }

  openService(service: AdminService): void {
    this.notice = '';
    this.dialog.open<RecordDialogResult | undefined>(RecordDialogComponent, {
      data: { kind: 'service', record: service, allowStatusChange: true }
    }).closed.subscribe(result => {
      if (result) {
        this.setStatus(service, result.action === 'disable' ? 'INACTIVE' : 'ACTIVE');
      }
    });
  }

  setStatus(service: AdminService, status: 'ACTIVE' | 'INACTIVE'): void {
    this.http.patch(
      `${environment.apiUrl}admin/services/${service.id}/status/`,
      { status }
    ).subscribe({
      next: () => {
        service.status = status;
        this.notice = status === 'INACTIVE'
          ? `"${service.service_name}" was disabled and is hidden from students.`
          : `"${service.service_name}" is visible to students again.`;
      },
      error: error => {
        this.error = error?.error?.detail || 'That service could not be updated.';
      }
    });
  }
}

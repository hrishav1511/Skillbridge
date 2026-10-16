import { Component, OnDestroy, OnInit } from '@angular/core';
import { Dialog } from '@angular/cdk/dialog';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';
import { apiLists } from '../../resources/apiLists';
import { ServiceCardComponent } from '../../resources/Modals/service-card/service-card.component';

@Component({
  selector: 'app-tutor-services',
  templateUrl: './tutor-services.component.html',
  styleUrls: ['./tutor-services.component.scss']
})
export class TutorServicesComponent implements OnInit, OnDestroy {
  services: any[] = [];
  loading = true;
  tutorId = localStorage.getItem('tutor_id') || '';
  selectedStatus: 'ALL' | 'UPCOMING' | 'RUNNING' | 'COMPLETED' = 'ALL';
  countdownTick = 0;
  private countdownTimer?: ReturnType<typeof setInterval>;

  constructor(
    private http: HttpClient,
    private dialog: Dialog,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadServices();
    this.countdownTimer = setInterval(() => this.countdownTick++, 1000);
  }

  ngOnDestroy(): void {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
    }
  }

  loadServices(): void {
    const params = new URLSearchParams();
    params.set('tutor_id', this.tutorId);
    if (this.selectedStatus !== 'ALL') {
      params.set('schedule_status', this.selectedStatus);
    }
    this.loading = true;
    this.http.get<any>(environment.apiUrl + apiLists.servicelist + '?' + params).subscribe({
      next: response => {
        this.services = response?.data || [];
        this.loading = false;
      },
      error: () => this.loading = false
    });
  }

  selectStatus(status: 'ALL' | 'UPCOMING' | 'RUNNING' | 'COMPLETED'): void {
    this.selectedStatus = status;
    this.loadServices();
  }

  goBack(): void {
    this.router.navigate(['/tutor/dashboard']);
  }

  editService(service: any): void {
    const dialogRef = this.dialog.open(ServiceCardComponent, {
      panelClass: ['profile-drawer'],
      data: { tutor_id: this.tutorId, item: service }
    });
    dialogRef.closed.subscribe(() => this.loadServices());
  }

  addService(): void {
    const dialogRef = this.dialog.open(ServiceCardComponent, {
      panelClass: ['profile-drawer'],
      data: { tutor_id: this.tutorId }
    });
    dialogRef.closed.subscribe(() => this.loadServices());
  }

  openDetails(service: any): void {
    const serviceId = service?.id || service?.service_id;
    if (serviceId) {
      this.router.navigate(['/tutor/services', serviceId], { state: { service } });
    }
  }

  mediaCount(service: any): number {
    const images = Array.isArray(service?.image_urls) ? service.image_urls.length : 0;
    const videos = Array.isArray(service?.video_urls) ? service.video_urls.length : 0;
    return images + videos + (service?.video_url && !videos ? 1 : 0);
  }

  isExpired(service: any): boolean {
    if (!service?.date) {
      return false;
    }
    const endOfDay = new Date(`${service.date}T23:59:59`);
    return !Number.isNaN(endOfDay.getTime()) && endOfDay < new Date();
  }

  serviceStart(service: any): Date | null {
    if (!service?.date) return null;
    const start = new Date(`${service.date}T${service.time || '00:00:00'}`);
    return Number.isNaN(start.getTime()) ? null : start;
  }

  serviceEnd(service: any): Date | null {
    if (!service?.date) return null;
    const end = new Date(`${service.date}T${service.end_time || service.time || '00:00:00'}`);
    return Number.isNaN(end.getTime()) ? null : end;
  }

  serviceStatus(service: any): 'UPCOMING' | 'RUNNING' | 'COMPLETED' {
    const apiStatus = String(service?.schedule_status || '').toUpperCase();
    if (apiStatus === 'UPCOMING' || apiStatus === 'RUNNING' || apiStatus === 'COMPLETED') {
      return apiStatus;
    }

    const start = this.serviceStart(service)?.getTime();
    const end = this.serviceEnd(service)?.getTime();
    if (!start || !end || Date.now() < start) return 'UPCOMING';
    return Date.now() < end ? 'RUNNING' : 'COMPLETED';
  }

  statusLabel(service: any): string {
    const status = this.serviceStatus(service);
    if (status === 'RUNNING') return 'Running';
    if (status === 'COMPLETED') return 'Completed';
    return 'Upcoming';
  }

  countdown(service: any): string {
    const start = this.serviceStart(service);
    if (!start) return 'Schedule unavailable';
    const remaining = start.getTime() - Date.now();
    if (remaining <= 0) return 'Starting now';
    const totalMinutes = Math.floor(remaining / 60000);
    const days = Math.floor(totalMinutes / 1440);
    const hours = Math.floor((totalMinutes % 1440) / 60);
    const minutes = totalMinutes % 60;
    const seconds = Math.floor((remaining % 60000) / 1000);
    if (days > 0) return `${days}d ${hours}h ${minutes}m`;
    return `${hours}h ${minutes}m ${seconds}s`;
  }
}

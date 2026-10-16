import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { Component, Inject } from '@angular/core';

export interface ServiceDayDialogData {
  /** The day being shown, as a Date. */
  date: Date;
  /** Services scheduled on that day. */
  services: any[];
}

export interface ServiceDayDialogResult {
  /** The service the user picked, if any. */
  service: any;
}

/**
 * Lists the services scheduled on one calendar day.
 *
 * Picking a service closes the dialog and hands it back, so the caller decides
 * where to navigate - the dialog stays reusable from either dashboard.
 */
@Component({
  selector: 'app-service-day-dialog',
  templateUrl: './service-day-dialog.component.html',
  styleUrls: ['./service-day-dialog.component.scss']
})
export class ServiceDayDialogComponent {

  constructor(
    @Inject(DIALOG_DATA) public data: ServiceDayDialogData,
    private dialogRef: DialogRef<ServiceDayDialogResult>
  ) {}

  get services(): any[] {
    return this.data?.services || [];
  }

  close(): void {
    this.dialogRef.close();
  }

  select(service: any): void {
    this.dialogRef.close({ service });
  }

  serviceName(service: any): string {
    return service?.service_name || service?.service?.service_name || 'Service';
  }

  /**
   * "14:30 - 15:30", or just the start when there is no end time.
   *
   * A tutor service carries its own times; a student booking keeps them on the
   * nested service, so read either shape.
   */
  timeRange(service: any): string {
    const start = this.trimSeconds(service?.time || service?.service?.time);
    const end = this.trimSeconds(service?.end_time || service?.service?.end_time);
    if (!start) {
      return 'Time not set';
    }
    return end ? `${start} - ${end}` : start;
  }

  status(service: any): string {
    return String(
      service?.schedule_status || service?.status || service?.booking_status || ''
    ).toUpperCase();
  }

  private trimSeconds(value: string | null | undefined): string {
    if (!value) {
      return '';
    }
    const parts = String(value).split(':');
    return parts.length >= 2 ? `${parts[0]}:${parts[1]}` : String(value);
  }
}

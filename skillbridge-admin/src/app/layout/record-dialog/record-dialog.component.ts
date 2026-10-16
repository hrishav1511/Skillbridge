import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { Component, Inject } from '@angular/core';

export type RecordKind = 'tutor' | 'service' | 'review';

export interface RecordDialogData {
  kind: RecordKind;
  record: any;
  /** Show the disable/enable control. Off for read-only viewing. */
  allowStatusChange?: boolean;
}

/** What the caller should do once the dialog closes. */
export interface RecordDialogResult {
  action: 'disable' | 'enable';
  record: any;
}

interface DetailRow {
  label: string;
  value: string;
}

/**
 * Read-only view of a tutor, service or review, with an optional
 * disable/enable action.
 *
 * Reports and the entity lists both need "show me the whole record", so the
 * same dialog serves both rather than each page growing its own.
 */
@Component({
  selector: 'app-record-dialog',
  templateUrl: './record-dialog.component.html',
  styleUrls: ['./record-dialog.component.scss']
})
export class RecordDialogComponent {
  constructor(
    @Inject(DIALOG_DATA) public data: RecordDialogData,
    private dialogRef: DialogRef<RecordDialogResult | undefined, RecordDialogComponent>
  ) {}

  get record(): any {
    return this.data?.record || {};
  }

  get title(): string {
    if (this.data.kind === 'tutor') {
      return this.record.user?.full_name || this.record.tutor_name || 'Tutor';
    }
    if (this.data.kind === 'service') {
      return this.record.service_name || 'Service';
    }
    return 'Reported review';
  }

  get isInactive(): boolean {
    const status = String(
      this.record.status || this.record.account_status || 'ACTIVE'
    ).toUpperCase();
    return status === 'INACTIVE';
  }

  get avatarUrl(): string | null {
    return this.record.profile_picture_url || this.record.tutor_profile_picture_url || null;
  }

  /** Images and videos, merging the legacy single-video column with the list. */
  get mediaItems(): { type: 'image' | 'video'; url: string }[] {
    const images: string[] = Array.isArray(this.record.image_urls)
      ? this.record.image_urls.filter((url: string) => !!url)
      : [];
    const videos: string[] = Array.isArray(this.record.video_urls)
      ? this.record.video_urls.filter((url: string) => !!url)
      : [];
    if (this.record.video_url && !videos.includes(this.record.video_url)) {
      videos.push(this.record.video_url);
    }
    return [
      ...images.map(url => ({ type: 'image' as const, url })),
      ...videos.map(url => ({ type: 'video' as const, url }))
    ];
  }

  get rows(): DetailRow[] {
    const record = this.record;
    const dash = (value: any) => (value === null || value === undefined || value === '' ? '—' : String(value));

    if (this.data.kind === 'tutor') {
      return [
        { label: 'Name', value: dash(record.user?.full_name || record.tutor_name) },
        { label: 'Email', value: dash(record.user?.email) },
        { label: 'Phone', value: dash(record.phone || record.user?.phone) },
        { label: 'Academic program', value: dash(record.academic_program) },
        { label: 'Teaching style', value: dash(record.teaching_style) },
        { label: 'Tags', value: record.tags?.length ? record.tags.join(', ') : '—' },
        { label: 'Average rating', value: dash(record.average_rating) },
        { label: 'Account status', value: dash(record.account_status || record.status) },
        { label: 'Approval status', value: dash(record.approval_status) },
        { label: 'Visibility', value: record.is_visible === undefined ? '—' : (record.is_visible ? 'Visible' : 'Hidden') },
        { label: 'Requests', value: record.accepting_requests === undefined ? '—' : (record.accepting_requests ? 'Accepting' : 'Paused') },
        { label: 'Tutor ID', value: dash(record.id || record.tutor_id) }
      ];
    }

    if (this.data.kind === 'service') {
      return [
        { label: 'Service', value: dash(record.service_name) },
        { label: 'Tutor', value: dash(record.tutor?.full_name) },
        { label: 'Price', value: record.price === undefined ? '—' : `€${record.price}` },
        { label: 'Level', value: dash(record.level) },
        { label: 'Date', value: dash(record.date) },
        { label: 'Time', value: `${dash(record.time)} – ${dash(record.end_time)}` },
        { label: 'Joining link', value: dash(record.joining_link) },
        { label: 'Tags', value: record.tags?.length ? record.tags.join(', ') : '—' },
        { label: 'Status', value: dash(record.status) },
        { label: 'Approval status', value: dash(record.approval_status) },
        { label: 'Service ID', value: dash(record.id || record.service_id) }
      ];
    }

    return [
      { label: 'Review type', value: dash(record.review_type) },
      { label: 'Rating', value: dash(record.review_rating) },
      { label: 'Comment', value: dash(record.review_comment) },
      { label: 'Reported by', value: dash(record.reporter_name) },
      { label: 'Review ID', value: dash(record.review_id) }
    ];
  }

  get description(): string | null {
    return this.record.description || this.record.bio || null;
  }

  onMediaError(event: Event): void {
    const target = event.target as HTMLElement | null;
    target?.parentElement?.classList.add('record-media__tile--broken');
  }

  toggleStatus(): void {
    this.dialogRef.close({
      action: this.isInactive ? 'enable' : 'disable',
      record: this.record
    });
  }

  close(): void {
    this.dialogRef.close(undefined);
  }
}

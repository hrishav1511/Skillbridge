import {
  Component,
  Inject,
  OnDestroy,
  OnInit
} from '@angular/core';

import {
  AbstractControl,
  FormBuilder,
  FormGroup,
  ValidationErrors,
  Validators
} from '@angular/forms';


import {
  HttpClient
} from '@angular/common/http';

import {
  environment
} from '../../../../environments/environment';
import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ToastrService } from 'ngx-toastr';
import { LoadingServiceService } from '../../services/loading-service.service';

function pastDateValidator(control: AbstractControl): ValidationErrors | null {
  if (!control.value) {
    return null;
  }
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const selected = new Date(`${control.value}T00:00:00`);
  return selected < today ? { pastDate: true } : null;
}

// `<input type="date">` accepts years well outside anything a service could be
// scheduled in (the API rejected "23423-03-24" with a 422), and pastDateValidator
// only guards the lower bound. Cap the upper bound so the form catches it first.
const MAX_YEARS_AHEAD = 5;

/*
 * Upload ceilings, mirroring MediaService on the API. Duplicated here only so
 * the form can refuse a file before spending a long upload on it; the server
 * enforces the same numbers and remains the real gate.
 */
const MAX_IMAGE_MB = 5;
const MAX_VIDEO_MB = 100;
const MAX_IMAGES = 8;
const MAX_VIDEOS = 3;

// Only fields the user can actually see and edit may carry a server error.
// Attaching one to a hidden control (tutor_id) would leave the form invalid
// with no way for the user to clear it, blocking every further submit.
const SERVER_ERROR_FIELDS = [
  'service_name',
  'description',
  'date',
  'time',
  'end_time',
  'price',
  'level',
  'joining_link'
];

function farFutureDateValidator(control: AbstractControl): ValidationErrors | null {
  if (!control.value) {
    return null;
  }
  const year = Number(String(control.value).split('-')[0]);
  const maxYear = new Date().getFullYear() + MAX_YEARS_AHEAD;
  if (!Number.isFinite(year) || year > maxYear) {
    return { farFutureDate: { maxYear } };
  }
  return null;
}

/** `<input type="time">` renders HH:MM only, so drop the seconds the API sends. */
function toInputTime(value: string | null | undefined): string {
  if (!value) {
    return '';
  }
  const parts = String(value).split(':');
  return parts.length >= 2 ? `${parts[0]}:${parts[1]}` : String(value);
}

/** The API accepts HH:MM, but it echoes HH:MM:SS back; send one shape either way. */
function normaliseTime(value: string | null | undefined): string {
  if (!value) {
    return '';
  }
  const parts = String(value).split(':');
  return parts.length === 2 ? `${value}:00` : String(value);
}

function serviceScheduleValidator(group: FormGroup): ValidationErrors | null {
  const date = group.get('date')?.value;
  const start = group.get('time')?.value;
  const end = group.get('end_time')?.value;

  if (start && end && start >= end) {
    return { timeRange: true };
  }

  if (date && start) {
    const now = new Date();
    const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    const currentTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    if (date === todayStr && start < currentTime) {
      return { pastStartTime: true };
    }
  }

  return null;
}

@Component({
  selector: 'app-service-card',
  templateUrl: './service-card.component.html',
  styleUrls: ['./service-card.component.scss']
})
export class ServiceCardComponent implements OnInit, OnDestroy {

  serviceForm!: FormGroup;

  isEditMode = false;
  isLoading = false;
  /** Why the last selected file was refused, shown under the pickers. */
  mediaError = '';
  /*
   * Subject tags for the service.
   *
   * The API has always accepted and stored these, the admin approval modal
   * renders them and the tutor search matches on them - but the form had no
   * field, so every service was created with an empty list.
   */
  tags: string[] = [];
  tagInput = '';
  selectedImageFiles: File[] = [];
  selectedVideoFiles: File[] = [];
  existingImageUrls: string[] = [];
  existingVideoUrls: string[] = [];
  private previewUrls = new Map<File, string>();
  readonly todayDate = new Date().toISOString().slice(0, 10);
  readonly maxDate = new Date(
    new Date().setFullYear(new Date().getFullYear() + MAX_YEARS_AHEAD)
  ).toISOString().slice(0, 10);
  /** Errors the API reported that do not map onto a specific form control. */
  serverError = '';

  constructor(
    private fb: FormBuilder,
    private http: HttpClient,
    private dialogRef: DialogRef<ServiceCardComponent>,
    @Inject(DIALOG_DATA) public data: any,
    private toastr:ToastrService,
    private loadingService:LoadingServiceService
  ) { }

  ngOnInit(): void {

    this.isEditMode = !!this.data?.item;

    this.initializeForm();

    if (this.isEditMode) {
      this.patchForm();
    }
  }

  initializeForm(): void {

    this.serviceForm = this.fb.group({
      tutor_id: [
        this.data?.tutor_id || '',
        Validators.required
      ],

      service_name: [
        '',
        Validators.required
      ],

      description: [
        '',
        Validators.required
      ],

      date: [
        '',
        [Validators.required, pastDateValidator, farFutureDateValidator]
      ],

      time: [
        '',
        Validators.required
      ],

      end_time: [
        '',
        Validators.required
      ],

      price: [
        0,
        [
          Validators.required,
          Validators.min(0)
        ]
      ],

      level: [
        'BEGINNER',
        Validators.required
      ],

      joining_link: [
        '',
        Validators.required
      ],

      image_urls: [[]],

      video_url: [''],

      video_urls: [[]]
    }, { validators: serviceScheduleValidator });
  }

  patchForm(): void {

    const service = this.data.item;

    this.serviceForm.patchValue({
      tutor_id: this.data.tutor_id,
      service_name: service.service_name,
      description: service.description,
      date: service.date,
      time: toInputTime(service.time),
      end_time: toInputTime(service.end_time),
      price: service.price,
      level: service.level,
      joining_link: service.joining_link,
      image_urls: service.image_urls || [],
      video_url: service.video_url || '',
      video_urls: service.video_urls || []
    });

    this.tags = Array.isArray(service.tags) ? [...service.tags] : [];

    this.existingImageUrls = Array.isArray(service.image_urls) ? [...service.image_urls] : [];
    this.existingVideoUrls = Array.isArray(service.video_urls) ? [...service.video_urls] : [];
  }

onImagesSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files || []);
    this.mediaError = '';

    for (const file of files) {
      const total = this.existingImageUrls.length + this.selectedImageFiles.length;
      if (total >= MAX_IMAGES) {
        this.mediaError = `You can attach at most ${MAX_IMAGES} images.`;
        break;
      }
      if (!file.type.startsWith('image/')) {
        this.mediaError = `"${file.name}" is not an image.`;
        continue;
      }
      if (file.size > MAX_IMAGE_MB * 1024 * 1024) {
        this.mediaError =
          `"${file.name}" is ${this.formatSize(file.size)}. Images must be ${MAX_IMAGE_MB}MB or smaller.`;
        continue;
      }
      this.selectedImageFiles = [...this.selectedImageFiles, file];
      this.previewUrls.set(file, URL.createObjectURL(file));
    }

    input.value = '';
  }

  onVideosSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files || []);
    this.mediaError = '';

    for (const file of files) {
      const total = this.existingVideoUrls.length + this.selectedVideoFiles.length;
      if (total >= MAX_VIDEOS) {
        this.mediaError = `You can attach at most ${MAX_VIDEOS} videos.`;
        break;
      }
      if (!file.type.startsWith('video/')) {
        this.mediaError = `"${file.name}" is not a video.`;
        continue;
      }
      if (file.size > MAX_VIDEO_MB * 1024 * 1024) {
        this.mediaError =
          `"${file.name}" is ${this.formatSize(file.size)}. Videos must be ${MAX_VIDEO_MB}MB or smaller.`;
        continue;
      }
      this.selectedVideoFiles = [...this.selectedVideoFiles, file];
      this.previewUrls.set(file, URL.createObjectURL(file));
    }

    input.value = '';
  }

  /** Human-readable size for the rejection message. */
  private formatSize(bytes: number): string {
    if (bytes >= 1024 * 1024 * 1024) {
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)}GB`;
    }
    return `${Math.max(1, Math.round(bytes / (1024 * 1024)))}MB`;
  }

    removeImage(index: number): void {
    const file = this.selectedImageFiles[index];

    if (file) {
      this.revokePreviewUrl(file);
    }

    this.selectedImageFiles.splice(index, 1);
  }

  removeExistingImage(index: number): void {
    this.existingImageUrls.splice(index, 1);
  }

  removeVideo(index: number): void {
    const file = this.selectedVideoFiles[index];

    if (file) {
      this.revokePreviewUrl(file);
    }

    this.selectedVideoFiles.splice(index, 1);
  }

  removeExistingVideo(index: number): void {
    this.existingVideoUrls.splice(index, 1);
  }

  addTag(): void {
    const value = this.tagInput.trim();
    if (!value || this.tags.some(tag => tag.toLowerCase() === value.toLowerCase())) {
      this.tagInput = '';
      return;
    }
    this.tags.push(value);
    this.tagInput = '';
  }

  removeTag(index: number): void {
    this.tags.splice(index, 1);
  }

  async buildFormData(): Promise<FormData> {
    this.loadingService.setLoading();
    const formValue = this.serviceForm.value;
    const tutorId = this.data?.tutor_id || formValue.tutor_id || '';
    const formData = new FormData();

    const textFields = {
      tutor_id: tutorId,
      service_name: formValue.service_name || '',
      description: formValue.description || '',
      date: formValue.date || '',
      time: normaliseTime(formValue.time),
      end_time: normaliseTime(formValue.end_time),
      price: formValue.price ?? 0,
      level: formValue.level || 'BEGINNER',
      joining_link: formValue.joining_link || '',
      tags: JSON.stringify(this.tags)
    };

    Object.entries(textFields).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        formData.append(key, String(value));
      }
    });

    this.selectedImageFiles.forEach((file) => {
      formData.append('images', file, file.name);
    });

    this.existingImageUrls.forEach((url) => {
      formData.append('existing_image_urls', url);
    });

    this.selectedVideoFiles.forEach((file) => {
      formData.append('videos', file, file.name);
    });

    this.existingVideoUrls.forEach((url) => {
      formData.append('existing_video_urls', url);
    });

    if (this.existingVideoUrls.length === 1) {
      formData.append('existing_video_url', this.existingVideoUrls[0]);
    }

    return formData;
  }

  getPreviewUrl(file: File): string {
    return this.previewUrls.get(file) || '';
  }

  private revokePreviewUrl(file: File): void {
    const previewUrl = this.previewUrls.get(file);

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      this.previewUrls.delete(file);
    }
  }

  ngOnDestroy(): void {
    this.selectedImageFiles.forEach((file) => this.revokePreviewUrl(file));
    this.selectedVideoFiles.forEach((file) => this.revokePreviewUrl(file));
  }


  async save(): Promise<void> {

    if (this.serviceForm.invalid) {
      this.serviceForm.markAllAsTouched();
      return;
    }
    this.serverError = '';
    this.isLoading = true;

    const formData = await this.buildFormData();

    if (this.isEditMode) {
      this.updateService(formData);
    } else {
      this.createService(formData);
    }
  }

  createService(formData: FormData): void {

    this.http.post(
      `${environment.apiUrl}service/create/`,
      formData
    )
      .subscribe({
        next: (response: any) => {

          this.isLoading = false;
          this.toastr.success('Service created , waiting for approval');
          this.dialogRef.close(response);
          this.loadingService.setSuccess();
        },

        error: (error) => {

          this.isLoading = false;
          this.applyServerErrors(error, 'Failed to create service.');
          this.loadingService.setError();
        }
      });
  }

  /**
   * Put the API's own validation messages in front of the user.
   *
   * A 422 body carries `detail: [{ field, message }]` naming the offending
   * field, so attach each one to its control and keep whatever is left over
   * (or a plain string detail) as a form-level message. Previously this only
   * reached the console, so a rejected create or update looked like nothing
   * had happened.
   */
  private applyServerErrors(error: any, fallback: string): void {
    this.serverError = '';
    const body = error?.error;
    const detail = body?.detail;
    const unmatched: string[] = [];

    if (Array.isArray(detail)) {
      detail.forEach((item: any) => {
        const field = item?.field;
        const message = item?.message || item?.msg || '';
        const control =
          field && SERVER_ERROR_FIELDS.includes(field)
            ? this.serviceForm.get(field)
            : null;
        if (control && message) {
          control.setErrors({ ...(control.errors || {}), server: message });
          control.markAsTouched();
        } else if (message) {
          unmatched.push(message);
        }
      });
    } else if (typeof detail === 'string' && detail) {
      // The validator layer reports a semicolon-joined "field: message" string
      // rather than the structured list, so split it back out.
      detail.split(';').forEach((part: string) => {
        const text = part.trim();
        if (!text) {
          return;
        }
        const separator = text.indexOf(':');
        const field = separator > -1 ? text.slice(0, separator).trim() : '';
        const control =
          field && SERVER_ERROR_FIELDS.includes(field)
            ? this.serviceForm.get(field)
            : null;
        if (control) {
          control.setErrors({
            ...(control.errors || {}),
            server: text.slice(separator + 1).trim()
          });
          control.markAsTouched();
        } else {
          unmatched.push(text);
        }
      });
    }

    if (!unmatched.length && typeof body?.message === 'string' && body.message) {
      unmatched.push(body.message);
    }

    this.serverError = unmatched.join(' ') || fallback;
    this.toastr.error(this.serverError, 'Error');
  }

  updateService(formData: FormData): void {
    this.http.put(
      `${environment.apiUrl}service/${this.data.item.id}/`,
      formData
    )
      .subscribe({
        next: (response: any) => {

          this.isLoading = false;
          this.toastr.success('Service updated , waiting for approval');
          this.dialogRef.close(response);
          this.loadingService.setSuccess();
        },

        error: (error) => {

          this.isLoading = false;
          this.applyServerErrors(error, 'Failed to update service.');
          this.loadingService.setError();
        }
      });
  }

  close(): void {
    this.dialogRef.close();
  }
}

import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { Component, Inject } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { apiLists } from '../../apiLists';
import { environment } from '../../../../environments/environment';
import { HttpClient } from '@angular/common/http';
import { LoadingServiceService } from '../../services/loading-service.service';

@Component({
  selector: 'app-my-details-card',
  templateUrl: './my-details-card.component.html',
  styleUrls: ['./my-details-card.component.scss']
})

export class MyDetailsCardComponent {
  profileForm!:FormGroup;

  isClosing = false;
  tags: string[] = [];
  tagInput = '';
  /** Mirrors the API's validators so long prose fails here, not in the database. */
  readonly bioMaxLength = 2000;
  readonly teachingStyleMaxLength = 1000;
  readonly phoneMaxLength = 50;
  /** Message from the API (including the "pending approval" confirmation). */
  serverError = '';

  constructor(
   private fb: FormBuilder,
    private dialogRef: DialogRef<MyDetailsCardComponent>,
    @Inject(DIALOG_DATA) public data: any,
    private http: HttpClient,
    private loadingService: LoadingServiceService
  ) {}

   ngOnInit(): void {

   this.profileForm = this.fb.group({
  full_name: [ this.data.full_name, [Validators.required, Validators.minLength(2)]],
  academic_program: [ this.data.academic_program, Validators.required],
  bio: [ this.data.bio, [
    Validators.required,
    Validators.minLength(30),
    Validators.maxLength(this.bioMaxLength)
  ]],
  phone: [ this.data.phone, [
    Validators.required,
    Validators.pattern(/^[0-9+\-\s()]{8,20}$/),
    Validators.maxLength(this.phoneMaxLength)
  ]],
  teaching_style: [ this.data.teaching_style, [
    Validators.required,
    Validators.minLength(20),
    Validators.maxLength(this.teachingStyleMaxLength)
  ]],
  is_visible: [this.data.is_visible],
  approval_status: [this.data.approval_status],
  accepting_requests: [this.data.accepting_requests]
});

    this.tags = [...(this.data.tags || [])];


//     this.profileForm.patchValue({
//   full_name: this.data.full_name,
//   academic_program: this.data.academic_program,
//   bio: this.data.bio,
//   phone: this.data.phone,
//   teaching_style: this.data.teaching_style,
//   is_visible: this.data.is_visible,
//   approval_status: this.data.approval_status,
//   accepting_requests: this.data.accepting_requests
// });
  }

  get f() {
  return this.profileForm.controls;
}

  /**
   * Show the API's validation messages on the fields they name.
   *
   * A 422 body carries `detail: [{ field, message }]`; a 400 (for example a
   * value the database refuses) carries a plain string. Both used to go only to
   * the console, leaving the user with a form that appeared to do nothing.
   */
  private applyServerErrors(error: any): void {
    const body = error?.error;
    const detail = body?.detail;
    const unmatched: string[] = [];

    if (Array.isArray(detail)) {
      detail.forEach((item: any) => {
        const message = item?.message || item?.msg || '';
        const control = item?.field ? this.profileForm.get(item.field) : null;
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
        const control = field ? this.profileForm.get(field) : null;
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

    this.serverError =
      unmatched.join(' ') || 'Could not save your profile. Please try again.';
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

  close() {
    this.isClosing = true;

    setTimeout(() => {
      this.dialogRef.close();
    }, 300);
  }

   save(): void {
    if (this.profileForm.invalid) {
      this.profileForm.markAllAsTouched();
      return;
    }
    this.serverError = '';
    this.loadingService.setLoading()
    const url = environment.apiUrl + apiLists.tutor_update + this.data?.tutor_id +'/';
    const payload = { ...this.profileForm.value, tags: this.tags };

     this.http.put(url, payload).subscribe({
    next: (response: any) => {
      // The update is staged as a revision for admin approval rather than
      // written straight to the profile, so hand the API's message back to the
      // caller. Closing silently made an accepted edit look like it was lost.
      this.dialogRef.close({
        ...payload,
        pendingApproval: true,
        message: response?.message || 'Profile update submitted for admin approval.'
      });
      this.loadingService.setSuccess()
    },
    error: (error) => {
      this.applyServerErrors(error);
      this.loadingService.setError()
    }
  });

  }


}

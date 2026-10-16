import { Component, OnInit } from '@angular/core';
import { AbstractControl, FormBuilder, FormGroup, ValidationErrors, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { apiLists } from '../../resources/apiLists';
import { environment } from '../../../environments/environment';
import { Router } from '@angular/router';
import { LoadingServiceService } from '../../resources/services/loading-service.service';
import { ToastrService } from 'ngx-toastr';

export function passwordComplexityValidator(control: AbstractControl): ValidationErrors | null {
  const value = control.value ?? '';

  if (!value || value.length < 8) {
    return null;
  }

  const hasUppercase = /[A-Z]/.test(value);
  const hasLowercase = /[a-z]/.test(value);
  const hasNumber = /\d/.test(value);
  const hasSpecialChar = /[^A-Za-z0-9]/.test(value);

  return hasUppercase && hasLowercase && hasNumber && hasSpecialChar ? null : { weakPassword: true };
}

@Component({
  selector: 'app-sign-in',
  templateUrl: './sign-in.component.html',
  styleUrls: ['./sign-in.component.scss']
})
export class SignInComponent implements OnInit {
  selectedRole: 'student' | 'tutor' = 'student';
  signupForm!: FormGroup;
  loading = false;
  error: string | null = null;
  success: string | null = null;
  roles: any[] = [];
  loadingRoles = false;
  showPassword = false;
  showConfirmPassword = false;
  tags: string[] = [];
  tagInput = '';
  academicPrograms: string[] = [];

  private creatorId = '3fa85f64-5717-4562-b3fc-2c963f66afa6';
  private roleIds = {
    student: '',
    tutor: ''
  };

  constructor(private fb: FormBuilder,
     private http: HttpClient,
      private router: Router,
       private loadingService: LoadingServiceService,
      private toastService: ToastrService) { }

  ngOnInit(): void {
    this.signupForm = this.fb.group({
      full_name: [null, Validators.required],
      email: [null, [Validators.required, Validators.email, Validators.pattern(/^[a-zA-Z0-9._%+-]+@hs-fulda\.de$/)]],
      phone: [null, [Validators.required, Validators.pattern(/^[0-9+\-\s()]{8,20}$/)]],
      password: [null, [Validators.required, Validators.minLength(8), passwordComplexityValidator]],
      confirm_password: [null, Validators.required],
      role_id: [this.roleIds.student, Validators.required],
      status: ['ACTIVE', Validators.required],
      has_registered: [true],
      is_verified: [true],
      field_of_study: [null],
      enrolled_university: [null],
      graduation_year: [null],
      bio: [null],
      teaching_style: [null],
      academic_program: [null],
    }, { validators: this.passwordMatchValidator });

    this.getRoles();
    this.getAcademicPrograms();
  }

  selectRole(role: 'student' | 'tutor'): void {
    this.signupForm.reset()
    this.signupForm.get('status')?.setValue('ACTIVE');
    this.selectedRole = role;
    this.tags = [];
    this.tagInput = '';
    const roleId = role === 'student' ? this.roleIds.student : this.roleIds.tutor;
    this.signupForm?.patchValue({ role_id: roleId });
    this.applyTutorValidators(role === 'tutor');
  }

  private applyTutorValidators(isTutor: boolean): void {
    const bio = this.signupForm.get('bio');
    const teachingStyle = this.signupForm.get('teaching_style');
    const academicProgram = this.signupForm.get('academic_program');

    if (isTutor) {
      bio?.setValidators([Validators.required, Validators.minLength(30)]);
      teachingStyle?.setValidators([Validators.required, Validators.minLength(20)]);
      academicProgram?.setValidators([Validators.required, Validators.maxLength(255)]);
    } else {
      bio?.clearValidators();
      teachingStyle?.clearValidators();
      academicProgram?.clearValidators();
    }

    bio?.updateValueAndValidity();
    teachingStyle?.updateValueAndValidity();
    academicProgram?.updateValueAndValidity();
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

  onSubmit(): void {
    if (this.signupForm.invalid) {
      this.signupForm.markAllAsTouched();
      this.logFormValidationStatus()
      return;
    }

    this.loading = true;
    this.error = null;
    this.success = null;

    // const payload = this.signupForm.value;
    const formValue = this.signupForm.getRawValue();

    let payload: any = {
      full_name: formValue.full_name,
      email: formValue.email,
      phone: formValue.phone,
      password: formValue.password,
      role_id: this.selectedRole === 'student' ? this.roleIds.student : this.roleIds.tutor,
      status: formValue.status,
      confirm_password: formValue.confirm_password,
      has_registered: formValue.has_registered,
      is_verified: formValue.is_verified
    };
    if(this.selectedRole === 'tutor') {
      payload = {
        ...payload,
        bio: formValue.bio,
        teaching_style: formValue.teaching_style,
        academic_program: formValue.academic_program,
        tags: this.tags
      };
    }

    if (this.selectedRole === 'student') {
      payload = {
        ...payload,
        field_of_study: formValue.field_of_study,
        enrolled_university: formValue.enrolled_university,
        graduation_year: formValue.graduation_year
      };
    }

    console.log('Registration payload:', payload);
    const url = environment.apiUrl + apiLists.user_register;
    this.loadingService.setLoading();
    this.http.post<any>(url, payload).subscribe({
      next: (response) => {
        const userId = response?.data?.id ?? response?.id ?? response?.user_id;

        this.loadingService.setSuccess();
        this.resetForm();
        this.router.navigate(['/auth/login']);
      },
      error: (error) => {
        this.loadingService.setError();
        console.error('Registration error:', error);
        this.toastService.error(error?.detail?.message || 'Registration failed. Please try again.');
        this.error = error?.error?.message || 'Registration failed. Please try again.';
      }
    });
  }

  private createTutorProfile(userId: string): void {
    const profilePayload = {
      user_id: userId,
      academic_program: this.signupForm.value.academic_program,
      bio: this.signupForm.value.bio,
      phone: this.signupForm.value.phone,
      teaching_style: this.signupForm.value.teaching_style,
      is_visible: this.signupForm.value.is_visible,
      approval_status: this.signupForm.value.approval_status,
      accepting_requests: this.signupForm.value.accepting_requests,
      tags: this.tags
    };
    const profileUrl = environment.apiUrl + apiLists.tutor_profile_create;
    this.http.post(profileUrl, profilePayload).subscribe({
      next: () => {
        this.loading = false;
        this.success = 'Tutor account created successfully.';
        this.resetForm();
        this.router.navigate(['/auth/login']);
      },
      error: (error) => {
        this.loading = false;
        console.error('Tutor profile error:', error);
        this.error = error?.error?.message || 'Tutor profile creation failed. Please try again.';
      }
    });
  }

  private resetForm(): void {
    this.signupForm.reset({
      created_by_id: this.creatorId,
      updated_by_id: this.creatorId,
      full_name: null,
      email: null,
      phone: null,
      password: null,
      confirm_password: null,
      role_id: this.selectedRole === 'student' ? this.roleIds.student : this.roleIds.tutor,
      status: 'ACTIVE',
      has_registered: true,
      is_verified: false,
      field_of_study: null,
      enrolled_university: null,
      graduation_year: null,
      academic_program: null,
      bio: null,
      teaching_style: null,
      is_visible: true,
      approval_status: 'PENDING',
      accepting_requests: true
    });
    this.tags = [];
    this.tagInput = '';
  }

  /**
   * Programs already in use on the platform.
   *
   * Offering the same values the tutor search filters by keeps a new tutor
   * findable; the field stays free-text so a genuinely new program can still
   * be entered.
   */
  private getAcademicPrograms(): void {
    this.http.get<{ data: string[] }>(environment.apiUrl + apiLists.academic_programs)
      .subscribe({
        next: (response) => this.academicPrograms = response?.data || [],
        error: () => this.academicPrograms = []
      });
  }

  private getRoles(): void {
    this.loadingRoles = true;
    this.http.get<any>(environment.apiUrl + apiLists.roles_list).subscribe({
      next: (response) => {
        const payload = response?.data ?? response;
        this.roles = Array.isArray(payload) ? payload : [];

        const studentRole = this.roles.find(role => String(role.slug || role.title || '').toLowerCase() === 'student');
        const tutorRole = this.roles.find(role => String(role.slug || role.title || '').toLowerCase() === 'tutor');

        if (studentRole?.id) {
          this.roleIds.student = studentRole.id;
        }
        if (tutorRole?.id) {
          this.roleIds.tutor = tutorRole.id;
        }

        this.signupForm.patchValue({
          role_id: this.selectedRole === 'student' ? this.roleIds.student : this.roleIds.tutor
        });
        this.loadingRoles = false;
      },
      error: () => {
        this.loadingRoles = false;
        this.roles = [];
      }
    });
  }

  get passwordCriteria(): { label: string; passed: boolean }[] {
    const value = this.signupForm?.get('password')?.value ?? '';

    return [
      { label: 'At least 8 characters', passed: value.length >= 8 },
      { label: 'One uppercase letter', passed: /[A-Z]/.test(value) },
      { label: 'One lowercase letter', passed: /[a-z]/.test(value) },
      { label: 'One number', passed: /\d/.test(value) },
      { label: 'One special character', passed: /[^A-Za-z0-9]/.test(value) }
    ];
  }

  togglePasswordVisibility(field: 'password' | 'confirm_password'): void {
    if (field === 'password') {
      this.showPassword = !this.showPassword;
      return;
    }

    this.showConfirmPassword = !this.showConfirmPassword;
  }

  private passwordMatchValidator(form: FormGroup): null | object {
    const password = form.get('password')?.value;
    const confirmPassword = form.get('confirm_password')?.value;
    return password && confirmPassword && password !== confirmPassword ? { passwordMismatch: true } : null;
  }

  logFormValidationStatus(): void {
    Object.keys(this.signupForm.controls).forEach(fieldName => {
      const control = this.signupForm.get(fieldName);

      console.log(
        `${fieldName}: ${control?.valid ? 'VALID' : 'INVALID'}`,
        {
          value: control?.value,
          errors: control?.errors
        }
      );
    });

    console.log(
      'Form Level Validation:',
      this.signupForm.errors ?? '✅ No form errors'
    );
  }
}

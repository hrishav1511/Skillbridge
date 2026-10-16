import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { environment } from '../../../environments/environment';
import { apiLists } from '../../resources/apiLists';
import { Router } from '@angular/router';
import { LoadingServiceService } from '../../resources/services/loading-service.service';
import { ChatService } from '../../resources/services/socket.service';
import { ToastrService } from 'ngx-toastr';
import { ProfileImageService } from '../../resources/services/profile-image.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent implements OnInit {
  loginForm!: FormGroup;
  /** Drives the reveal toggle next to the password field. */
  showPassword = false;
  roles:any[] = [];
  loadingRoles: boolean = false;
  selectedRole:String = 'student';
  private roleIds = {
    student: '',
    tutor: ''
  };
  constructor(private fb: FormBuilder,
    private http: HttpClient,
    private router: Router,
    private loadingService: LoadingServiceService,
    private chatservice:ChatService,
    private toastr:ToastrService,
    private profileImageService: ProfileImageService
  ) { }

  ngOnInit(): void {
    this.loginForm = this.fb.group({
      email: [null,[Validators.required, Validators.email,Validators.pattern(/^[a-zA-Z0-9._%+-]+@hs-fulda\.de$/)]],
      password: [null,Validators.required],
      role_id:[null,Validators.required]
    });
    this.getRoles();
  }

  private getRoles(): void {
      this.loadingService.setLoading();
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
          this.loginForm.patchValue({
            role_id: this.selectedRole === 'student' ? this.roleIds.student : this.roleIds.tutor
          });
        this.loadingService.setSuccess()
        },
        error: () => {
          this.loadingService.setError();
          this.toastr.error('Something went wrong');
          this.roles = [];
        }
      });
    }

  continueAsGuest(): void {
    const guestUser = {
      id: 'guest-user',
      full_name: 'Guest User',
      email: 'guest@hs-fulda.de',
      role: 'guest'
    };

    localStorage.setItem('userData', JSON.stringify(guestUser));
    localStorage.setItem('user_id', JSON.stringify(guestUser.id));
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('token_type');
    localStorage.removeItem('token_expires_in');
    localStorage.setItem('tutor_id', '');
    localStorage.setItem('user_ROLE', 'GUEST');

    this.toastr.success('Continuing as guest');
    this.router.navigate(['/student/dashboard']);
    this.loadingService.setSuccess();
  }

  onSubmit(){
    if (this.loginForm.invalid) {
      this.toastr.error('Please fill in all required fields correctly.');
      this.loginForm.markAllAsTouched()
      return;
    }
    this.loadingService.setLoading();
    this.loginForm.get('role_id')?.setValue(this.selectedRole === 'student' ? this.roleIds.student : this.roleIds.tutor);

    const profileUrl = environment.apiUrl + apiLists.user_login;
    this.http.post(profileUrl, this.loginForm.value).subscribe({
      next: (response:any) => {
        // The avatar URL sits alongside `user` on the login payload, not inside
        // it. Fold it in so ProfileImageService finds it on the next reload,
        // and publish it now so the navbar fills without one.
        localStorage.setItem('userData', JSON.stringify({
          ...response.data.user,
          profile_picture_url: response.data.profile_picture_url ?? null
        }));
        this.profileImageService.updateProfileImage(response.data.profile_picture_url);
        localStorage.setItem('user_id',JSON.stringify(response.data.user_id));
        localStorage.setItem('access_token', response.data.access_token);
        localStorage.setItem('refresh_token', response.data.refresh_token);
        localStorage.setItem('token_type', response.data.token_type);
        localStorage.setItem('token_expires_in', String(response.data.expires_in));
        localStorage.setItem('tutor_id',response.data.tutor_id);
        localStorage.setItem('student_id',response.data.student_id);
          this.toastr.success('Successfully Logged In')
        const url = this.selectedRole === 'student' ? '/student/dashboard' : '/tutor/dashboard';
        localStorage.setItem('user_ROLE',this.selectedRole === 'student'? 'STUDENT':'TUTOR');
          this.chatservice.connect(response.data.user_id);

        this.router.navigate([url]);
        this.loadingService.setSuccess()
      },
      error: (error) => {
        this.loadingService.setError()
        // console.error('Tutor profile error:', error);
        this.toastr.error(error?.detail || 'Login failed. Please try again.');
      }
    });
  }

}

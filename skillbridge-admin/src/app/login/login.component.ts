import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { environment } from 'src/environments/environment';
import { apilists } from '../resources/ApiList';
import { HttpClient } from '@angular/common/http';
import { FormBuilder, Validators } from '@angular/forms';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent {
  loginForm: any;
  /** Drives the reveal toggle next to the password field. */
  showPassword = false;
  constructor(
    private route:Router,
    private http:HttpClient,
    private fb: FormBuilder,
    private router:Router

  ){
    this.loginForm = this.fb.group({
      email: [null,[Validators.required, Validators.email,Validators.pattern(/^[a-zA-Z0-9._%+-]+@hs-fulda\.de$/)]],
      password: [null,Validators.required]
    })
  }

  gotodashboard(){
    const profileUrl = environment.apiUrl + apilists.user_login;
    this.http.post(profileUrl, this.loginForm.value).subscribe({
      next: (response:any) => {
        
        localStorage.setItem('userData',JSON.stringify(response.data.user));
        localStorage.setItem('user_id',JSON.stringify(response.data.user_id));
        localStorage.setItem('access_token', response.data.access_token);
        localStorage.setItem('refresh_token', response.data.refresh_token);
        localStorage.setItem('token_type', response.data.token_type);
        localStorage.setItem('token_expires_in', String(response.data.expires_in));
        localStorage.setItem('tutor_id',response.data.tutor_id);
        localStorage.setItem('user_ROLE', String(response.data.role?.slug || '').toUpperCase());

        this.router.navigate(['/panel']);
      },
      error: (error) => {
        console.error('Tutor profile error:', error);
      }
    });
    this.route.navigate([]);
  }
}

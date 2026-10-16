import { Injectable } from '@angular/core';
import {
  HttpErrorResponse,
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest
} from '@angular/common/http';

import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { Router } from '@angular/router';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  constructor(
    private router: Router
  ) { }

  intercept(
    req: HttpRequest<any>,
    next: HttpHandler
  ): Observable<HttpEvent<any>> {

    const accessToken = localStorage.getItem('access_token');

    // No token → send request normally
    if (!accessToken) {
      return next.handle(req);
    }

    // Add Authorization header
    const authReq = req.clone({
      setHeaders: {
        Authorization: `Bearer ${accessToken}`
      }
    });

    return next.handle(authReq).pipe(

      catchError((error: HttpErrorResponse) => {

        if (error.status === 401) {

          localStorage.removeItem('access_token');
          localStorage.removeItem('token_type');
          localStorage.removeItem('token_expires_in');
          localStorage.removeItem('userData');
          localStorage.removeItem('user_id');
          localStorage.removeItem('tutor_id');
          localStorage.removeItem('student_id');

          this.router.navigate(['auth/login']);
        }

        return throwError(() => error);
      })

    );
  }
}



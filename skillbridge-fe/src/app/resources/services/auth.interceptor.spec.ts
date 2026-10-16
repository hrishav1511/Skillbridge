import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { HttpErrorResponse, HttpRequest } from '@angular/common/http';
import { BehaviorSubject, throwError } from 'rxjs';
import { Router } from '@angular/router';
import { ToastrService } from 'ngx-toastr';

import { AuthInterceptor } from './auth.interceptor';
import { ChatService } from './socket.service';
import { environment } from '../../../environments/environment';

describe('AuthInterceptor', () => {
  let interceptor: AuthInterceptor;
  let httpMock: HttpTestingController;
  let router: Router;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        AuthInterceptor,
        {
          provide: Router,
          useValue: {
            navigate: jasmine.createSpy('navigate')
          }
        },
        {
          provide: ChatService,
          useValue: {
            connect: jasmine.createSpy('connect'),
            disconnect: jasmine.createSpy('disconnect')
          }
        },
        {
          provide: ToastrService,
          useValue: {
            error: jasmine.createSpy('error'),
            success: jasmine.createSpy('success')
          }
        }
      ]
    });

    interceptor = TestBed.inject(AuthInterceptor);
    httpMock = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    localStorage.clear();
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('should be created', () => {
    expect(interceptor).toBeTruthy();
  });

  it('should reject queued requests when refresh fails', () => {
    localStorage.setItem('refresh_token', 'refresh-token');

    const request = new HttpRequest('GET', 'https://example.com/protected');
    const next = { handle: jasmine.createSpy('handle') };

    (interceptor as any).isRefreshing = true;
    (interceptor as any).refreshTokenSubject = new BehaviorSubject<string | null>(null);

    const queuedError = jasmine.createSpy('queuedError');
    (interceptor as any).handle401Error(request, next).subscribe({
      error: queuedError
    });

    (interceptor as any).isRefreshing = false;
    (interceptor as any).handle401Error(request, next).subscribe({
      error: jasmine.createSpy('refreshError')
    });

    const refreshRequest = httpMock.expectOne(environment.apiUrl + 'refresh-token/');
    expect(refreshRequest.request.method).toBe('POST');
    expect(refreshRequest.request.body).toEqual({ refresh_token: 'refresh-token' });
    refreshRequest.flush(
      { detail: 'Token expired' },
      { status: 401, statusText: 'Unauthorized' }
    );

    expect(queuedError).toHaveBeenCalled();
    expect(router.navigate).toHaveBeenCalledWith(['/auth/login']);
  });

  it('sends the access token on guest-readable reads when signed in', () => {
    localStorage.setItem('access_token', 'access-token');
    const next = {
      handle: jasmine.createSpy('handle').and.returnValue(new BehaviorSubject(null))
    };

    interceptor.intercept(
      new HttpRequest('GET', environment.apiUrl + 'tutor/tutors/?favorite_only=true'),
      next
    ).subscribe();

    const forwarded = next.handle.calls.mostRecent().args[0] as HttpRequest<unknown>;
    expect(forwarded.headers.get('Authorization')).toBe('Bearer access-token');
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('still allows guest-readable reads through without a service', () => {
    const next = {
      handle: jasmine.createSpy('handle').and.returnValue(new BehaviorSubject(null))
    };

    interceptor.intercept(
      new HttpRequest('GET', environment.apiUrl + 'tutor/tutors/'),
      next
    ).subscribe();

    const forwarded = next.handle.calls.mostRecent().args[0] as HttpRequest<unknown>;
    expect(forwarded.headers.has('Authorization')).toBeFalse();
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('does not attempt a refresh when an anonymous request is rejected', () => {
    localStorage.setItem('refresh_token', 'existing-refresh-token');
    const guestError = new HttpErrorResponse({
      status: 401,
      statusText: 'Unauthorized',
      error: { detail: 'Authorization header missing' }
    });
    const next = {
      handle: jasmine.createSpy('handle').and.returnValue(throwError(() => guestError))
    };
    const receivedError = jasmine.createSpy('receivedError');

    interceptor.intercept(
      new HttpRequest('GET', environment.apiUrl + 'tutor/tutors/'),
      next
    ).subscribe({ error: receivedError });

    expect(receivedError).toHaveBeenCalledWith(guestError);
    httpMock.expectNone(environment.apiUrl + 'refresh-token/');
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('never sends a token to the pre-auth endpoints', () => {
    localStorage.setItem('access_token', 'access-token');
    const next = {
      handle: jasmine.createSpy('handle').and.returnValue(new BehaviorSubject(null))
    };

    interceptor.intercept(
      new HttpRequest('POST', environment.apiUrl + 'user/login/', {}),
      next
    ).subscribe();

    const forwarded = next.handle.calls.mostRecent().args[0] as HttpRequest<unknown>;
    expect(forwarded.headers.has('Authorization')).toBeFalse();
  });

  it('redirects to login when a protected request has no service', () => {
    const next = {
      handle: jasmine.createSpy('handle').and.returnValue(new BehaviorSubject(null))
    };

    interceptor.intercept(
      new HttpRequest('GET', environment.apiUrl + 'dashboard/student/'),
      next
    ).subscribe();

    expect(router.navigate).toHaveBeenCalledWith(['/auth/login']);
  });

  it('should preserve a public login 401 without attempting token refresh', () => {
    localStorage.setItem('refresh_token', 'existing-refresh-token');
    const loginError = new HttpErrorResponse({
      status: 401,
      statusText: 'Unauthorized',
      error: { detail: 'Invalid email or password' }
    });
    const next = {
      handle: jasmine.createSpy('handle').and.returnValue(
        throwError(() => loginError)
      )
    };
    const receivedError = jasmine.createSpy('receivedError');

    interceptor.intercept(
      new HttpRequest('POST', environment.apiUrl + 'user/login/', {}),
      next
    ).subscribe({ error: receivedError });

    expect(receivedError).toHaveBeenCalledWith(loginError);
    httpMock.expectNone(environment.apiUrl + 'refresh-token/');
    expect(localStorage.getItem('refresh_token')).toBe('existing-refresh-token');
    expect(router.navigate).not.toHaveBeenCalled();
  });

  /*
   * Guest browsing.
   *
   * A browse endpoint missing from guestReadableRoutes does not merely 401:
   * the interceptor redirects to /auth/login, throwing the guest out of the
   * page. That shipped twice - first for tutor/academic-programs/, then again
   * for tutor/tags/ when the subject filter was added - so the whole set a
   * guest-reachable page calls is pinned here.
   */
  const GUEST_BROWSE_ENDPOINTS = [
    'tutor/tutors/',            // tutor list + view-tutor profile
    'service/services/',        // service list
    'tutor/academic-programs/', // program filter dropdown
    'tutor/tags/',              // subject filter dropdown
    'review/tutor/',            // reviews on a tutor profile
    'review/service/'           // reviews on a service
  ];

  GUEST_BROWSE_ENDPOINTS.forEach((endpoint) => {
    it(`lets a signed-out guest GET ${endpoint} without being sent to login`, () => {
      localStorage.clear();
      const next = {
        handle: jasmine.createSpy('handle').and.returnValue(
          new BehaviorSubject<any>({})
        )
      };

      interceptor.intercept(
        new HttpRequest('GET', environment.apiUrl + endpoint),
        next
      ).subscribe();

      expect(router.navigate).not.toHaveBeenCalled();
      expect(next.handle).toHaveBeenCalled();
    });
  });

  it('still sends a signed-out user to login for an account-only endpoint', () => {
    localStorage.clear();
    const next = {
      handle: jasmine.createSpy('handle').and.returnValue(
        new BehaviorSubject<any>({})
      )
    };

    interceptor.intercept(
      new HttpRequest('GET', environment.apiUrl + 'service-booking/service-bookings/'),
      next
    ).subscribe();

    expect(router.navigate).toHaveBeenCalledWith(['/auth/login']);
  });
});

import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpErrorResponse
} from '@angular/common/http';

import {
  catchError,
  Observable,
  throwError,
  BehaviorSubject,
  filter,
  take,
  switchMap
} from 'rxjs';

import { Router } from '@angular/router';
import { ChatService } from './socket.service';
import { ToastrService } from 'ngx-toastr';
import { apiLists } from '../apiLists';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  /*
   * Pre-auth endpoints. A token is never sent to these, and a 401 from them
   * is a real answer (bad credentials), not an expired session.
   */
  private readonly preAuthRoutes = [
    apiLists.roles_list,
    apiLists.user_login,
    apiLists.user_register
  ];

  /*
   * NOTE: every endpoint a guest-reachable page calls must be listed
   * here. A missing entry does not merely 401 - the branch below
   * redirects to /auth/login, so the guest is thrown out of the page.
   * auth.interceptor.spec.ts pins the full set.
   */
  /*
   * Readable without signing in, but personalised when the caller *is* signed
   * in (own id, favourites, own hidden profile). The token must still be sent
   * so the backend can tell a guest from a logged-in user.
   */
  private readonly guestReadableRoutes = [
    apiLists.tutorlist,
    apiLists.servicelist,
    apiLists.academic_programs,
    apiLists.tutor_tags,
    apiLists.tutor_review,
    apiLists.service_review
  ];

  // Prevent multiple refresh requests
  private isRefreshing = false;

  // Holds the new access token for requests waiting for refresh
  private refreshTokenSubject =
    new BehaviorSubject<string | null>(null);

  constructor(
    private router: Router,
    private chatservice: ChatService,
    private toastr: ToastrService,
    private http: HttpClient
  ) {}

  intercept(
    request: HttpRequest<unknown>,
    next: HttpHandler
  ): Observable<HttpEvent<unknown>> {

    const isPreAuth = this.preAuthRoutes.some(route =>
      request.url.includes(route)
    );

    /*
     * Requests that are allowed to go out without credentials. Everything else
     * needs a session.
     */
    const allowsGuests = isPreAuth || (
      request.method === 'GET' &&
      this.guestReadableRoutes.some(route => request.url.includes(route))
    );

    /*
     * Send the token whenever we have one. A route being publicly *readable*
     * is not a reason to drop the caller's identity: the backend uses it to
     * return the user's own id, their favourites, and their own profile even
     * when it is hidden from the marketplace.
     */
    const accessToken = isPreAuth
      ? null
      : localStorage.getItem('access_token');

    /*
     * No session, and this route needs one.
     */
    if (!accessToken && !allowsGuests) {

      this.router.navigate(['/auth/login']);

      return next.handle(request);
    }

    const authRequest = accessToken
      ? this.addToken(request, accessToken)
      : request;

    /*
     * Send request
     */
    return next.handle(authRequest).pipe(

      catchError((error: HttpErrorResponse) => {

        /*
         * Only a request we actually authenticated can have an expired token.
         * A 401 on an anonymous request is the expected answer, not a session
         * problem, so it must not trigger a refresh or a logout.
         */
        if (error.status === 401 && accessToken) {

          /*
           * Don't try to refresh if this request
           * was already the refresh request.
           */
          if (request.url.includes('/refresh')) {

            this.logout();

            return throwError(() => error);
          }

          /*
           * Try to refresh access token
           */
          return this.handle401Error(
            authRequest,
            next
          );
        }

        return throwError(() => error);
      })
    );
  }

  /**
   * Handles 401 errors.
   */
  private handle401Error(
    request: HttpRequest<unknown>,
    next: HttpHandler
  ): Observable<HttpEvent<unknown>> {

    /*
     * If no refresh is currently happening,
     * this request becomes responsible for refreshing.
     */
    if (!this.isRefreshing) {

      this.isRefreshing = true;

      /*
       * Clear the current subject value so
       * other requests know they need to wait.
       */
      this.refreshTokenSubject.next(null);

      const refreshToken =
        localStorage.getItem('refresh_token');

      /*
       * No refresh token available
       */
      if (!refreshToken) {

        this.isRefreshing = false;

        this.logout();

        return throwError(
          () => new Error('Refresh token not found')
        );
      }

      return this.http.post<any>(
        environment.apiUrl + 'refresh-token/',
        { refresh_token: refreshToken },
      ).pipe(

        switchMap((response) => {

          /*
           * Get new access token
           */
          const newAccessToken =
            response.access_token;

          /*
           * Save new access token
           */
          localStorage.setItem(
            'access_token',
            newAccessToken
          );

          /*
           * Refresh is complete
           */
          this.isRefreshing = false;

          /*
           * Tell waiting requests about
           * the new access token.
           */
          this.refreshTokenSubject.next(
            newAccessToken
          );

          /*
           * Retry the original request
           * using the new access token.
           */
          const retryRequest =
            this.addToken(
              request,
              newAccessToken
            );

          return next.handle(retryRequest);
        }),

        catchError((refreshError) => {

          /*
           * Refresh token is invalid/expired
           * or refresh request failed.
           */
          this.isRefreshing = false;

          const failedRefreshSubject = this.refreshTokenSubject;
          this.refreshTokenSubject = new BehaviorSubject<string | null>(null);
          failedRefreshSubject.error(refreshError);

          this.logout();

          return throwError(
            () => refreshError
          );
        })
      );

    } else {

      /*
       * Another request is already refreshing
       * the access token.
       *
       * Wait until the new token is available.
       */
      return this.refreshTokenSubject.pipe(

        filter(
          token => token !== null
        ),

        take(1),

        switchMap((newAccessToken) => {

          /*
           * Retry this request with
           * the newly received token.
           */
          const retryRequest =
            this.addToken(
              request,
              newAccessToken!
            );

          return next.handle(retryRequest);
        })
      );
    }
  }

  /**
   * Adds Authorization header.
   */
  private addToken(
    request: HttpRequest<unknown>,
    token: string
  ): HttpRequest<unknown> {

    return request.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  /**
   * Logout user when refresh token
   * is no longer valid.
   */
  private logout(): void {

    localStorage.clear();

    // this.chatservice.disconnect();

    // this.toastr.error(
    //   'Session expired. Please log in again.'
    // );

    this.router.navigate(['/auth/login']);
  }
}

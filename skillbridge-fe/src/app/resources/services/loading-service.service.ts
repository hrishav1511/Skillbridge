import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { LoadingState } from '../models';

@Injectable({
  providedIn: 'root'
})
export class LoadingServiceService {

  constructor() { }

  private loadingStateSubject =
    new BehaviorSubject<LoadingState>(LoadingState.IDLE);

  loadingState$ = this.loadingStateSubject.asObservable();

  setLoading(): void {
    this.loadingStateSubject.next(LoadingState.LOADING);
  }

  setSuccess(): void {
    this.loadingStateSubject.next(LoadingState.SUCCESS);
  }

  setError(): void {
    this.loadingStateSubject.next(LoadingState.ERROR);
  }

  reset(): void {
    this.loadingStateSubject.next(LoadingState.IDLE);
  }
}

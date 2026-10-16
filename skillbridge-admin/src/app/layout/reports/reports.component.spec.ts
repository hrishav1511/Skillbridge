import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { DialogModule } from '@angular/cdk/dialog';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';
import { convertToParamMap } from '@angular/router';

import { ReportsComponent } from './reports.component';
import { RecordDialogComponent } from '../record-dialog/record-dialog.component';
import { environment } from 'src/environments/environment';

describe('ReportsComponent', () => {
  let component: ReportsComponent;
  let fixture: ComponentFixture<ReportsComponent>;
  let http: HttpTestingController;

  /** Build the component with a given ?tab= value already on the URL. */
  function setUp(tab?: string): void {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      declarations: [ReportsComponent, RecordDialogComponent],
      imports: [HttpClientTestingModule, RouterTestingModule, DialogModule],
      providers: [{
        provide: ActivatedRoute,
        useValue: {
          queryParamMap: of(convertToParamMap(tab ? { tab } : {}))
        }
      }]
    });
    fixture = TestBed.createComponent(ReportsComponent);
    component = fixture.componentInstance;
    http = TestBed.inject(HttpTestingController);
  }

  beforeEach(() => setUp());

  /** Answer the three list requests ngOnInit fires. */
  function flushInitialLoad(
    tutors: any[] = [], services: any[] = [], reviews: any[] = []
  ): void {
    component.ngOnInit();
    http.expectOne(`${environment.apiUrl}report/tutor/`).flush({ data: tutors });
    http.expectOne(`${environment.apiUrl}report/service/`).flush({ data: services });
    http.expectOne(`${environment.apiUrl}report/review/`).flush({ data: reviews });
  }

  afterEach(() => http.verify());

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('loads all three report queues', () => {
    flushInitialLoad(
      [{ id: 'r1', tutor_name: 'Ada', reason: 'x' }],
      [{ id: 'r2', service_name: 'Algebra', reason: 'y' }],
      [{ id: 'r3', review_type: 'tutor', review_rating: 1, reason: 'z' }]
    );

    expect(component.tutorReports.length).toBe(1);
    expect(component.serviceReports.length).toBe(1);
    expect(component.reviewReports.length).toBe(1);
  });

  it('preselects the tab named in the query string', () => {
    setUp('review');
    flushInitialLoad();

    expect(component.activeTab).toBe('review');
  });

  it('falls back to the tutor tab when the query string names nothing valid', () => {
    setUp('nonsense');
    flushInitialLoad();

    expect(component.activeTab).toBe('tutor');
  });

  it('sends nothing until a deletion is confirmed', () => {
    flushInitialLoad([{ id: 'r1', tutor_name: 'Ada', reason: 'x' }]);

    component.askToDelete('tutor', 'r1', 'resolved', 'Ada');

    // Staging must not touch the API; http.verify() in afterEach fails if
    // anything was sent.
    expect(component.pendingAction).toBeTruthy();
  });

  it('cancelling drops the action without calling the API', () => {
    flushInitialLoad();

    component.askToDelete('service', 'r2', 'discard', 'Algebra');
    component.cancelAction();

    expect(component.pendingAction).toBeNull();
  });

  it('confirming a discard deletes the report and reloads', () => {
    flushInitialLoad();

    component.askToDelete('service', 'r2', 'discard', 'Algebra');
    component.confirmAction();

    const request = http.expectOne(`${environment.apiUrl}report/service/r2/`);
    expect(request.request.method).toBe('DELETE');
    request.flush({});

    flushInitialLoadResponses();
    expect(component.pendingAction).toBeNull();
  });

  it('confirming Resolved deletes a review report', () => {
    flushInitialLoad();

    component.askToDelete('review', 'r3', 'resolved', 'this review');
    component.confirmAction();

    const request = http.expectOne(`${environment.apiUrl}report/review/r3/`);
    expect(request.request.method).toBe('DELETE');
    request.flush({});

    flushInitialLoadResponses();
    expect(component.notice).toContain('resolved');
  });

  it('surfaces a failed action instead of silently reloading', () => {
    flushInitialLoad();

    component.askToDelete('tutor', 'r1', 'discard', 'Ada');
    component.confirmAction();

    http.expectOne(`${environment.apiUrl}report/tutor/r1/`)
      .flush({ detail: 'Admin access required.' }, { status: 403, statusText: 'Forbidden' });

    expect(component.error).toBe('Admin access required.');
    expect(component.pendingAction).toBeNull();
  });

  it('opening a tutor report fetches the full tutor record', () => {
    flushInitialLoad();

    component.openReport('tutor', { id: 'r1', tutor_id: 't1', tutor_name: 'Ada' });

    const request = http.expectOne(`${environment.apiUrl}tutor/tutors/?tutor_id=t1`);
    expect(request.request.method).toBe('GET');
    request.flush({ data: [{ id: 't1', user: { full_name: 'Ada' } }] });
  });

  /** Answer the reload that follows a successful action. */
  function flushInitialLoadResponses(): void {
    http.expectOne(`${environment.apiUrl}report/tutor/`).flush({ data: [] });
    http.expectOne(`${environment.apiUrl}report/service/`).flush({ data: [] });
    http.expectOne(`${environment.apiUrl}report/review/`).flush({ data: [] });
  }
});

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TutorDashboardComponent } from './tutor-dashboard.component';
import { SkillBridgeTestingModule } from '../../../testing/skillbridge-testing.module';
import { HttpTestingController } from '@angular/common/http/testing';
import { environment } from '../../../environments/environment';

describe('TutorDashboardComponent', () => {
  let component: TutorDashboardComponent;
  let fixture: ComponentFixture<TutorDashboardComponent>;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [TutorDashboardComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(TutorDashboardComponent);
    component = fixture.componentInstance;
    http = TestBed.inject(HttpTestingController);
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  /** Drive the private calendar builder without going through HTTP. */
  function buildWith(services: any[], year: number, month: number): void {
    component.calendarServices = services;
    component.viewYear = year;
    component.viewMonth = month;
    (component as any).buildCalendar();
  }

  function cellFor(day: number): any {
    return component.calendarWeeks
      .reduce((all, week) => all.concat(week), [] as any[])
      .find(cell => cell.day === day);
  }

  it('places services on their own date', () => {
    buildWith([{ id: 's1', date: '2026-03-14', time: '10:00:00' }], 2026, 2);
    expect(cellFor(14).services.length).toBe(1);
    expect(cellFor(13).services.length).toBe(0);
  });

  it('keeps every day of the month once the grid is built', () => {
    buildWith([], 2026, 1); // February 2026 has 28 days
    const days = component.calendarWeeks
      .reduce((all, week) => all.concat(week), [] as any[])
      .filter(cell => cell.day !== null)
      .map(cell => cell.day);
    expect(days.length).toBe(28);
    expect(days[0]).toBe(1);
    expect(days[days.length - 1]).toBe(28);
  });

  it('navigates across a year boundary in both directions', () => {
    buildWith([], 2026, 11); // December
    component.nextMonth();
    expect(component.viewMonth).toBe(0);
    expect(component.viewYear).toBe(2027);

    component.previousMonth();
    expect(component.viewMonth).toBe(11);
    expect(component.viewYear).toBe(2026);
  });

  it('jumps back to the present month', () => {
    const today = new Date();
    buildWith([], 2020, 0);
    expect(component.isViewingCurrentMonth).toBeFalse();

    component.goToToday();

    expect(component.viewYear).toBe(today.getFullYear());
    expect(component.viewMonth).toBe(today.getMonth());
    expect(component.isViewingCurrentMonth).toBeTrue();
  });

  it('marks today only in the month that actually contains it', () => {
    const today = new Date();
    buildWith([], today.getFullYear(), today.getMonth());
    expect(cellFor(today.getDate()).isToday).toBeTrue();

    // The same day number in another month must not be flagged.
    const other = new Date(today.getFullYear() - 1, today.getMonth(), 1);
    buildWith([], other.getFullYear(), other.getMonth());
    expect(cellFor(today.getDate()).isToday).toBeFalse();
  });

  it('accepts a pending request through the workflow endpoint', () => {
    component.updateBooking({ id: 'booking-1' }, 'accept');
    http.expectOne(`${environment.apiUrl}service-booking/booking-1/accept/`).flush({});
    http.expectOne(`${environment.apiUrl}service-booking/service-bookings/`).flush({ data: [] });
    http.expectOne(`${environment.apiUrl}dashboard/tutor/`).flush({ data: {} });
    expect(component.serviceRequests).toEqual([]);
  });
});

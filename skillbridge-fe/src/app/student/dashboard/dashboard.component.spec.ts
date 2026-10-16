import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';

import { DashboardComponent } from './dashboard.component';
import { SkillBridgeTestingModule } from '../../../testing/skillbridge-testing.module';

describe('DashboardComponent', () => {
  let component: DashboardComponent;
  let fixture: ComponentFixture<DashboardComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [DashboardComponent],
      imports: [SkillBridgeTestingModule],
      schemas: [NO_ERRORS_SCHEMA]
    });
    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  /** Drive the private calendar builder directly. */
  function buildWith(bookings: any[], year: number, month: number): void {
    component.booked_service_list = bookings;
    component.viewYear = year;
    component.viewMonth = month;
    (component as any).buildCalendar();
  }

  function cellFor(day: number): any {
    return component.calendarWeeks
      .reduce((all, week) => all.concat(week), [] as any[])
      .find(cell => cell.day === day);
  }

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('navigates across a year boundary in both directions', () => {
    buildWith([], 2026, 11);
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
  });

  it('marks today only in the month that actually contains it', () => {
    const today = new Date();
    buildWith([], today.getFullYear(), today.getMonth());
    expect(cellFor(today.getDate()).isToday).toBeTrue();

    const other = new Date(today.getFullYear() - 1, today.getMonth(), 1);
    buildWith([], other.getFullYear(), other.getMonth());
    expect(cellFor(today.getDate()).isToday).toBeFalse();
  });

  it('places bookings on the day they are scheduled', () => {
    buildWith(
      [{ id: 'b1', scheduled_start_at: '2026-03-14T10:00:00Z', service: { service_name: 'Maths' } }],
      2026,
      2
    );
    expect(cellFor(14).bookings?.length).toBe(1);
    expect(cellFor(13).bookings?.length).toBe(0);
  });

  it('keeps the whole month once the grid is built', () => {
    buildWith([], 2026, 1); // February 2026: 28 days
    const days = component.calendarWeeks
      .reduce((all, week) => all.concat(week), [] as any[])
      .filter(cell => cell.day !== null);
    expect(days.length).toBe(28);
  });
});

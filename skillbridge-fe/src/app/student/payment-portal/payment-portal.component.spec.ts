import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpTestingController } from '@angular/common/http/testing';

import { PaymentPortalComponent } from './payment-portal.component';
import { SkillBridgeTestingModule } from '../../../testing/skillbridge-testing.module';
import { environment } from '../../../environments/environment';
import { apiLists } from '../../resources/apiLists';

describe('PaymentPortalComponent', () => {
  let component: PaymentPortalComponent;
  let fixture: ComponentFixture<PaymentPortalComponent>;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [PaymentPortalComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(PaymentPortalComponent);
    component = fixture.componentInstance;
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('books straight from review without a card-details step', fakeAsync(() => {
    component.service = { id: 'svc-1', price: 20 };
    component.confirmBooking();

    // The card step is gone: confirming moves review -> processing directly.
    expect(component.step).toBe('processing');

    tick(3000);
    const request = http.expectOne(`${environment.apiUrl}${apiLists.service_booking}`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ service_id: 'svc-1' });
    request.flush({});

    expect(component.step).toBe('success');
    http.verify();
  }));

  it('surfaces the server detail when the booking is rejected', fakeAsync(() => {
    component.service = { id: 'svc-1', price: 20 };
    component.confirmBooking();
    tick(3000);

    http.expectOne(`${environment.apiUrl}${apiLists.service_booking}`)
      .flush({ detail: 'You have already booked this service.' },
        { status: 400, statusText: 'Bad Request' });

    expect(component.step).toBe('error');
    expect(component.bookingErrorMessage).toBe('You have already booked this service.');
    http.verify();
  }));
});

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ReviewsComponent } from './reviews.component';
import { SkillBridgeTestingModule } from '../../../../testing/skillbridge-testing.module';
import { Dialog } from '@angular/cdk/dialog';

describe('ReviewsComponent', () => {
  let component: ReviewsComponent;
  let fixture: ComponentFixture<ReviewsComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [ReviewsComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(ReviewsComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('opens the report dialog against the right review for authenticated users', () => {
    localStorage.setItem('access_token', 'token');
    component.data = { type: 'service' };
    const dialog = TestBed.inject(Dialog);
    const open = spyOn(dialog, 'open').and.callThrough();

    component.reportReview({ id: 'review-1' });

    // The dialog now owns validation and the POST, so the component's job is
    // to hand it the correct endpoint and label.
    expect(open).toHaveBeenCalled();
    const config = open.calls.mostRecent().args[1] as any;
    expect(config.data.endpoint).toBe('report/review/service/review-1/');
    expect(config.data.label).toBe('Review');
    localStorage.removeItem('access_token');
  });

  it('does not offer reporting to guests', () => {
    localStorage.removeItem('access_token');
    localStorage.setItem('role', 'GUEST');
    expect(component.canReportReviews()).toBeFalse();
    localStorage.removeItem('role');
  });
});

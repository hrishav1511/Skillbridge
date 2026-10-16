import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DashboardComponent } from './dashboard.component';
import { SkillBridgeTestingModule } from '../../../testing/skillbridge-testing.module';
import { HttpTestingController } from '@angular/common/http/testing';
import { environment } from 'src/environments/environment';

describe('DashboardComponent', () => {
  let component: DashboardComponent;
  let fixture: ComponentFixture<DashboardComponent>;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [DashboardComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    http = TestBed.inject(HttpTestingController);
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('does not act on reports itself - it links to the Reports page', () => {
    // The unconfirmed one-click "Remove review"/"Dismiss" buttons were replaced
    // by a Manage link, so deleting a report now goes through the confirmation
    // on the Reports page. Nothing here may mutate a report.
    expect((component as any).resolveReviewReport).toBeUndefined();
  });
});

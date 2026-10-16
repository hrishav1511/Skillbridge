import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ViewTutorComponent } from './view-tutor.component';
import { SkillBridgeTestingModule } from '../../../testing/skillbridge-testing.module';

describe('ViewTutorComponent', () => {
  let component: ViewTutorComponent;
  let fixture: ComponentFixture<ViewTutorComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [ViewTutorComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(ViewTutorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

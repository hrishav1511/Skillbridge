import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TutorComponent } from './tutor.component';
import { SkillBridgeTestingModule } from '../../testing/skillbridge-testing.module';

describe('TutorComponent', () => {
  let component: TutorComponent;
  let fixture: ComponentFixture<TutorComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [TutorComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(TutorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

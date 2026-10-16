import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TutorListComponent } from './tutor-list.component';
import { SkillBridgeTestingModule } from '../../../../testing/skillbridge-testing.module';

describe('TutorListComponent', () => {
  let component: TutorListComponent;
  let fixture: ComponentFixture<TutorListComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [TutorListComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(TutorListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

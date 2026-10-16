import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MyProfileComponent } from './my-profile.component';
import { SkillBridgeTestingModule } from '../../../testing/skillbridge-testing.module';

describe('MyProfileComponent', () => {
  let component: MyProfileComponent;
  let fixture: ComponentFixture<MyProfileComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [MyProfileComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(MyProfileComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

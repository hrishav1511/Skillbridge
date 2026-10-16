import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MyDetailsCardComponent } from './my-details-card.component';
import { SkillBridgeTestingModule } from '../../../../testing/skillbridge-testing.module';

describe('MyDetailsCardComponent', () => {
  let component: MyDetailsCardComponent;
  let fixture: ComponentFixture<MyDetailsCardComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [MyDetailsCardComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(MyDetailsCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

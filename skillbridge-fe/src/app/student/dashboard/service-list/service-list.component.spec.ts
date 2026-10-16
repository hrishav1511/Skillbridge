import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ServiceListComponent } from './service-list.component';
import { SkillBridgeTestingModule } from '../../../../testing/skillbridge-testing.module';

describe('ServiceListComponent', () => {
  let component: ServiceListComponent;
  let fixture: ComponentFixture<ServiceListComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [ServiceListComponent],
      imports: [SkillBridgeTestingModule]
    });
    fixture = TestBed.createComponent(ServiceListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

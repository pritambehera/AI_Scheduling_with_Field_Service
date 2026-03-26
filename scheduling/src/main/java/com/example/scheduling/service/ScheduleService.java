package com.example.scheduling.service;

import com.example.scheduling.dto.ScheduleDto;
import com.example.scheduling.dto.ScheduleRequest;
import reactor.core.publisher.Mono;

public interface ScheduleService {
    Mono<ScheduleDto> propose(ScheduleRequest request);
    Mono<ScheduleDto> replan(ScheduleRequest request);
    Mono<ScheduleDto> commit(ScheduleRequest request);
    Mono<ScheduleDto> getById(String id);
}

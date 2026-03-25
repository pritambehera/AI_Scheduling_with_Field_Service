package com.example.scheduling.service.impl;

import com.example.scheduling.dto.ScheduleDto;
import com.example.scheduling.dto.ScheduleRequest;
import com.example.scheduling.service.ScheduleService;

public class ScheduleServiceImpl  implements ScheduleService {
    private final WebClient orchestrationClient = WebClient.builder()
            .baseUrl("http://localhost:8080")
            .build();


    @Override
    public Mono<ScheduleDto> propose(ScheduleRequest request) {
        return orchestrationClient.post()
                .uri("/api/v1/orchestrate")
                .bodyValue(request)
                .retrieve()
                .bodyToMono(ScheduleDto.class);
    }

    @Override
    public Mono<ScheduleDto> replan(ScheduleRequest request) {
        return propose(request);
    }

    @Override
    public Mono<ScheduleDto> commit(ScheduleRequest request) {
        return commit(request);
    }

    @Override
    public Mono<ScheduleDto> getById(ScheduleRequest request) {
        return Mono.empty();
    }

}

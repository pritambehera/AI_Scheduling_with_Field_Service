package com.example.scheduling.controller;

import ch.qos.logback.core.rolling.helper.MonoTypedConverter;
import com.example.scheduling.dto.ScheduleDto;
import com.example.scheduling.dto.ScheduleRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;
import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/v1/schedules")
@RequiredArgsConstructor
public class ScheduleController {

    private final ScheduleService scheduleService;

    @PostMapping("/propose")
    public Mono<ResponseEntity<ScheduleDto>> propose(@RequestBody ScheduleRequest request) {
        return scheduleService.propose(request)
                .map(ResponseEntity::ok);
    }
    @PostMapping("/replan")
    public Mono<ResponseEntity<ScheduleDto>> replan(@RequestBody ScheduleRequest request) {
        return scheduleService.replan(request)
                .map(ResponseEntity::ok);
    }
    @PostMapping("/commit")
    public Mono<ResponseEntity<ScheduleDto>> commit(@RequestBody ScheduleRequest request) {
        return scheduleService.commit(request)
                .map(ResponseEntity::ok);
    }
    @GetMapping("/{id}")
    public Mono<ResponseEntity<ScheduleDto>> getById(@PathVariable String id) {
        return scheduleService.getById(id)
                .map(ResponseEntity::ok);
    }

}

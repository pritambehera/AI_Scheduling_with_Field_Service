package com.example.scheduling.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.ToString;

import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
@ToString
public class ScheduleRequest {
    private  String region;
    private int horizonHours;
    private String objective;
    private Map<String, Object> constraints;

}

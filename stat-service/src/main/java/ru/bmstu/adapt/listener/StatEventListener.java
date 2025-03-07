package ru.bmstu.adapt.listener;

import ru.bmstu.adapt.domain.DetectionObject;
import ru.bmstu.adapt.domain.StatEvent;
import ru.bmstu.adapt.domain.StatEventType;
import ru.bmstu.adapt.service.DetectionObjectService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.List;

import static ru.bmstu.adapt.config.RabbitConfig.STAT_FANOUT_QUEUE_NAME;

@Component
@Slf4j
@RequiredArgsConstructor
public class StatEventListener {

    private final ObjectMapper objectMapper;
    private final DetectionObjectService detectionObjectService;

    @RabbitListener(queues = {STAT_FANOUT_QUEUE_NAME})
    public void receiveFromFanout(Message message) {
        try {
            StatEvent statEvent = objectMapper.readValue(message.getBody(), StatEvent.class);

            if (statEvent.getType() == StatEventType.OBJECT_DETECTION) {
                saveDetectionObject(statEvent);
            }
        } catch (Exception exc) {
            log.error("Stat-event was not generated -> {}", exc.getMessage());
        }
    }

    private void saveDetectionObject(StatEvent statEvent) {
        String userId = (String) statEvent.getAttributes().get("userId");
        String detectionProcessId = (String) statEvent.getAttributes().get("detectionProcessId");
        String clazz = (String) statEvent.getAttributes().get("clazz");
        Double score = (Double) statEvent.getAttributes().get("score");
        Integer numFrame = (Integer) statEvent.getAttributes().get("iteration");
        Integer numObject = (Integer) statEvent.getAttributes().get("numObject");
        List boxList = (List) statEvent.getAttributes().get("box");
        String image = (String) statEvent.getAttributes().get("image");

        Integer[] box = new Integer[4];
        for (int i = 0; i < boxList.size(); i++) {
            box[i] = ((Double) boxList.get(i)).intValue();
        }

        DetectionObject detectionObject = DetectionObject.builder()
                .userId(userId)
                .detectionProcessId(detectionProcessId)
                .clazz(clazz)
                .score(score)
                .numFrame(numFrame)
                .numObject(numObject)
                .box(box)
                .image(image)
                .createdDate(LocalDateTime.now())
                .build();

        detectionObjectService.save(detectionObject);
    }

}

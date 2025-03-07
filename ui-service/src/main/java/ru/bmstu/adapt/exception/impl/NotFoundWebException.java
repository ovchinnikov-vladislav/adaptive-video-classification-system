package ru.bmstu.adapt.exception.impl;

import ru.bmstu.adapt.exception.AbstractWebHandleableException;
import org.springframework.http.HttpStatus;

public class NotFoundWebException extends AbstractWebHandleableException {

    public NotFoundWebException(String message) {
        super(message, HttpStatus.NOT_FOUND);
    }

    public NotFoundWebException(String message, Throwable throwable) {
        super(message, throwable, HttpStatus.NOT_FOUND);
    }
}

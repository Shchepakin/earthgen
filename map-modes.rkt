#lang typed/racket

(provide (all-defined-out))

(require "map-mode.rkt"
         "planet/planet.rkt"
         "planet-color.rkt")

(define-map-modes terrain planet-water?
  (topography color-topography))

(define-map-modes climate planet-climate?
  (vegetation color-supported-vegetation)
  (temperature color-temperature)
  (insolation color-insolation)
  (aridity color-aridity)
  (humidity color-humidity)
  (precipitation color-precipitation))
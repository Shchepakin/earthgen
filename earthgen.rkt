#lang racket

(require vraid/require)

(require/provide
         racket/flonum
         "planet-display.rkt"
         "planet/planet-generation.rkt"
         "planet/grid/grid-create.rkt"
         "planet/planet.rkt"
         "terrain-gen.rkt"
         "terrain-dsl.rkt")

(provide (all-defined-out))

(define (algorithms)
  (load-algorithms (file->algorithm grids) "terrain-generation"))

(define (available-algorithms)
  (hash-keys (algorithms)))

(define (algorithm key)
  (hash-ref (algorithms) key))

(define (stream-take s n)
  (define (f s ls n)
    (if (zero? n)
        (reverse ls)
        (f
         (stream-rest s)
         (cons (stream-first s) ls)
         (- n 1))))
  (f s '() n))

(define grids
  (letrec ([stream
            (λ (grid)
              (stream-cons
               grid
               (stream (subdivided-grid grid))))]
           [grid-stream (stream (n-grid 0))])
    (λ (n)
      (reverse (stream-take grid-stream (+ n 1))))))

(define ((heightmap f) grids)
  (grid/heightmap
   (first grids)
   (f grids)))

(define ((generate-climate parameters) planet)
  ((singular-climate parameters (thunk* #f)) planet))

(define default-planet
  (let ([climate-parameters
         (climate-parameters/kw
          #:axial-tilt 0.0
          #:acceptable-delta 0.05
          #:precipitation-factor 1.0
          #:humidity-half-life-days 5.0
          #:seasons-per-cycle 16)])
    (compose
     (generate-climate climate-parameters)
     planet/rivers
     (planet/sea-level 0.0)
     (heightmap->planet 6000.0 (flvector 1.0 0.0 0.0))
     (heightmap ((eval-terrain-function (algorithm 'default)) ""))
     grids)))

#lang racket
(require racket/gui/base
         "terrain-create.rkt"
         "terrain-functions.rkt"
         "grid-structs.rkt"
         "grid-functions.rkt"
         "grid-list.rkt"
         "vector3.rkt"
         "logic.rkt"
         "math.rkt"
         math/flonum
         sgl/gl)

(define-values (display-width display-height) (get-display-size))
(define planet (let* ([grids (n-grid-list 8)]
                      [grid (force (grid-list-first (force grids)))]
                      [continent (first (terrain-create
                                         (terrain-parameters "earth" 2 2000.0 0.65)
                                         grids))]
                      [mountain (terrain-elevation-lower
                                 300.0
                                 (first (terrain-create
                                         (terrain-parameters "mtn" 5 2500.0 0.7)
                                         grids)))]
                      [final-terrain (terrain
                                      (vector-map (lambda (n) 
                                                    (let ([continent-elevation (vector-ref (terrain-tile-elevation continent) n)]
                                                          [mountain-elevation (vector-ref (terrain-tile-elevation mountain) n)])
                                                      (+ continent-elevation
                                                         (if (both true?
                                                                   (< 0 mountain-elevation)
                                                                   (< 0 continent-elevation))
                                                             mountain-elevation
                                                             0))))
                                                  (build-vector (grid-tile-count grid) identity))
                                      #f)])
                 (list grid final-terrain)))

(define (vector3->vertex v)
  (glVertex3d (flvector-ref v 0)
              (flvector-ref v 1)
              (flvector-ref v 2)))
  

(define (tile-vertices grid tile)
  (vector3->vertex (tile-coordinates tile))
  (for ([c (tile-corners tile)])
    (vector3->vertex (corner-coordinates (grid-corner grid c))))
  (vector3->vertex (corner-coordinates (grid-corner grid (tile-corner tile 0)))))

(define (vector3->color v)
  (glColor3f (flvector-ref v 0)
             (flvector-ref v 1)
             (flvector-ref v 2)))

(define (color-interpolate col-one col-two d)
  (vector3+ (vector3-scale col-one (- 1.0 d)) (vector3-scale col-two d)))

(define water-surface
  (vector3 0.0 0.4 0.8))
(define water-deep
  (vector3 0.0 0.0 0.3))
(define land-low
  (vector3 0.5 0.8 0.0))
(define land-high
  (vector3 0.2 0.2 0.1))

(define (tile-color elevation)
  (let ([col (if (< 0 elevation)
                 (color-interpolate land-low land-high (exact->inexact (min 1.0 (/ elevation 3000.0))))
                 (color-interpolate water-surface water-deep (exact->inexact (min 1.0 (/ elevation -3000.0)))))])
    (vector3->color col)))

(define (draw-opengl)
  (glFrontFace GL_CCW)
  (glEnable GL_CULL_FACE)
  (glCullFace GL_BACK)
  (glClearColor 0.0 0.0 0.0 0.0)
  (glClear GL_COLOR_BUFFER_BIT)
 
  (glShadeModel GL_SMOOTH)
 
  (glMatrixMode GL_PROJECTION)
  (glLoadIdentity)
  (let ([mx (* 1.1 (exact->inexact (/ display-width display-height)))]
        [my 1.1])
    (glOrtho (- mx) mx (- my) my -2.0 2.0))
  (glMatrixMode GL_MODELVIEW)
  (glLoadIdentity)
  
  (let* ([grid (first planet)]
         [terrain (second planet)]
         [tiles (grid-tiles->vector grid)]
         [corners (grid-corners->vector grid)])
    (for ([tile tiles])
      (glBegin GL_TRIANGLE_FAN)
      (tile-color (- (vector-ref (terrain-tile-elevation terrain) (tile-id tile)) 500.0))
      (tile-vertices grid tile)
      (glEnd))
    ))

(define frame
  (new frame%
       [label "Earthgen"]
       [width display-width]
       [height display-height]
       [style '(no-resize-border
                no-caption
                no-system-menu)]))

(define canvas
  (class* canvas% ()
    (inherit with-gl-context swap-gl-buffers)
    (define/override (on-paint)
      (with-gl-context (lambda () (draw-opengl) (swap-gl-buffers))))
    (define/override (on-size width height)
      (with-gl-context (lambda () (glViewport 0 0 width height))))
    (super-instantiate () (style '(gl)))))

(define gl-context (new canvas [parent frame]))

(send frame maximize #t) 
(send frame show #t)
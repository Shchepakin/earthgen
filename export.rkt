#lang racket

(require vraid/math
         "earthgen.rkt")

; use even numbers
(define planet-characteristic-size 4)

; don't use high number of seasons if planet-characteristic-size is big
(define my-climate-parameters (climate-parameters/kw
    #:axial-tilt (/ pi 8)
    #:acceptable-delta 0.05
    #:precipitation-factor 1.0
    #:humidity-half-life-days 5.0
    #:seasons-per-cycle 4))

(define gen-planet
  (compose
   (generate-climate my-climate-parameters)
   planet/rivers
   (planet/sea-level 0.0)
   (heightmap->planet 6371.0 (flvector 0.0 0.0 1.0))
   (heightmap ((eval-terrain-function (algorithm 'default)) ""))
   grids))

(define (repeat f arg n)
    (if (> n 0) (repeat f (f arg) (- n 1)) arg))

(define next-season (climate-next my-climate-parameters (thunk* #f)))

(define (season planet s) (repeat next-season planet s))

(define (range n) tile-count(build-list n values))

(define (pentagon? n) (< n 12))

(define (adjecent-tiles planet n)
    (let ([sides (if (pentagon? n) 5 6)])
      (map (lambda (i) (tile-tile planet n i)) (range sides))))

(define (next-tile-in-direction planet n0 n1)
  (let* ([x0 ((grid-tile-coordinates planet) n0)]
         [x1 ((grid-tile-coordinates planet) n1)]
         [ns (adjecent-tiles planet n0)])
    (argmin (lambda (n)
              (let ([x ((grid-tile-coordinates planet) n)])
                (if (eq? n1 n) 0
                    (flvector3-angle x x1)))) ns)))

(define (get-size planet)
  (let ([st 0]
        [sp 6])
    (for/and ([i (tile-count planet)]
          #:final (let ([t (repeat (lambda (ns)
                                      (list (apply next-tile-in-direction planet ns) (list-ref ns 1)))
                                    (list st sp) i)])
                    (equal? (list-ref t 0) sp)))
      (+ i 1))))

(define (tile-direction-list planet length n0 n1)
  (for/list ([i length])
    (list-ref (repeat (lambda (ns) (list (apply next-tile-in-direction planet ns) (list-ref ns 1))) (list n0 n1) i) 0)))

(define (triangle planet n0 n1 n2)
  (let ([side0 (tile-direction-list planet (get-size planet) n0 n1)]
        [side1 (tile-direction-list planet (get-size planet) n0 n2)])
    (for/list ([i (length side0)]
               [s0 side0]
               [s1 side1])
      (tile-direction-list planet (+ i 1) s0 s1))))

(define (slice planet n0 n1 n2 n3 n4 n5)
  (list (triangle planet n0 n1 n2)
        (triangle planet n1 n3 n2)
        (triangle planet n1 n4 n3)
        (triangle planet n4 n5 n3)))

(define (print-tile planet n x y out)
  (let* ([xy (string-append "      (" (number->string x) ", " (number->string y) "): {")]
        [id (string-append "'id': " (number->string n) ", ")]
        [sl (string-append "'sunlight': " (number->string (tile-sunlight planet n)) ", ")]
        [temp (string-append "'temperature': " (number->string (tile-temperature planet n)) ", ")]
        [hum (string-append "'humidity': " (number->string (tile-humidity planet n)) ", ")]
        [prec (string-append "'precipitation': " (number->string (tile-precipitation planet n)) ", ")]
        [area (string-append "'area':" (number->string (tile-area planet n)) ", ")]
        [snw (string-append "'snow':" (number->string (tile-snow planet n)) ", ")]
        [lai (string-append "'lai':" (number->string (tile-leaf-area-index planet n)) ", ")]
        [elv (string-append "'elevation':" (number->string (tile-elevation planet n)) ", ")]
        [coords (map (lambda (i) (corner-coordinates planet (tile-corner planet n i))) (range (if (pentagon? n) 5 6)))]
        [print-coords (string-join (map (lambda (el) (string-join (map (lambda (i) (number->string (flvector-ref el i))) (range (flvector-length el))) ", "
                                                                  #:before-first "("
                                                                  #:after-last "),")) coords)
               #:before-first "'coords': ("
               #:after-last ")},")])    
    (displayln (string-append xy id sl temp hum prec area snw lai elv print-coords) out)))
        
(define (print-slice planet n0 n1 n2 n3 n4 n5 out)
  (let ([size (get-size planet)])
    (begin
      (displayln "    {" out)
      (for ([i 4]
            [tr (slice  planet n0 n1 n2 n3 n4 n5)])
        (for ([j (length tr)]
              [row tr])
          (for ([k (length row)]
                [t row])
            (cond
              [(eq? i 0) (print-tile planet t (* -1 k) j out)]
              [(eq? i 1) (print-tile planet t (* -1 j) (- (+ j (- size 1)) k) out)]
              [(eq? i 2) (print-tile planet t (* -1 k) (+ (- size  1) j) out)]
              [(eq? i 3) (print-tile planet t (* -1 j) (- (+ j (* 2 (- size 1))) k) out)]))))
      (displayln "    }," out))))


(define (print-all-slices planet out)
  (let ([slices (list (list planet 2 11 9 0 6 1 out)
                      (list planet 2 7 11 6 10 1 out)
                      (list planet 2 3 7 10 8 1 out)
                      (list planet 2 5 3 8 4 1 out)
                      (list planet 2 9 5 4 0 1 out))])
    (for ([sl slices]) (apply print-slice sl))))

(define (print-season planet out)
    (begin
      (displayln "  [" out)
      (print-all-slices planet out)
      (displayln "  ]," out)))

(define (print-planet planet out)
    (begin
      (displayln "planet = [" out)
      (for ([s (climate-parameters-seasons-per-cycle (planet-climate-parameters planet))])
         (print-season (season planet s) out))
      (displayln "]" out)))

(define p8 (gen-planet planet-characteristic-size))

(define output (open-output-file #:mode 'text #:exists 'replace "./earthgen_export.py"))
(print-planet p8 output)

(close-output-port output)

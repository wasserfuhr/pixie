(ns pixie.stdlib)

(def reset! -reset!)

(def map (fn map [f]
             (fn [xf]
                 (fn
                  ([] (xf))
                  ([result] (xf result))
                  ([result item] (xf result (f item)))))))

(def conj (fn conj
           ([] [])
           ([result] result)
           ([result item] (-conj result item))))

(def transduce (fn transduce
              ([f coll]
                (let [result (-reduce coll f (f))]
                      (f result)))

              ([xform rf coll]
                (let [f (xform rf)
                      result (-reduce coll f (f))]
                      (f result)))
              ([xform rf init coll]
                (let [f (xform rf)
                      result (-reduce coll f init)]
                      (f result)))))

(def reduce (fn [rf init col]
              (-reduce col rf init)))


(def interpose
     (fn interpose [val]
       (fn [xf]
           (let [first? (atom true)]
                (fn
                 ([] (xf))
                 ([result] (xf result))
                 ([result item] (if @first?
                                    (do (reset! first? false)
                                        (xf result item))
                                  (xf (xf result val) item))))))))


(def preserving-reduced
  (fn [rf]
    (fn [a b]
      (let [ret (rf a b)]
        (if (reduced? ret)
          (reduced ret)
          ret)))))

(def cat
  (fn cat [rf]
    (let [rrf (preserving-reduced rf)]
      (fn cat-inner
        ([] (rf))
        ([result] (rf result))
        ([result input]
           (reduce rrf result input))))))


(def seq-reduce (fn seq-reduce
                  [coll f init]
                  (loop [init init
                         coll (seq coll)]
                    (if (reduced? init)
                      @init
                      (if (seq coll)
                        (recur (f init (first coll))
                               (seq (next coll)))
                        init)))))

(def indexed-reduce (fn indexed-reduce
                      [coll f init]
                      (let [max (count coll)]
                      (loop [init init
                             i 0]
                        (if (reduced? init)
                          @init
                          (if (-eq i max)
                            init
                            (recur (f init (nth coll i)) (+ i 1))))))))

(extend -reduce Cons seq-reduce)
(extend -reduce PersistentList seq-reduce)
(extend -reduce LazySeq seq-reduce)

(comment (extend -reduce Array indexed-reduce))

(extend -str Bool
  (fn [x]
    (if (identical? x true)
      "true"
      "false")))

(extend -str Nil (fn [x] "nil"))
(extend -reduce Nil (fn [self f init] init))
(extend -hash Nil (fn [self] 100000))

(extend -hash Integer hash-int)

(extend -eq Integer -num-eq)

(def ordered-hash-reducing-fn
  (fn ordered-hash-reducing-fn
    ([] (new-hash-state))
    ([state] (finish-hash-state state))
    ([state itm] (update-hash-ordered! state itm))))

(def unordered-hash-reducing-fn
  (fn unordered-hash-reducing-fn
    ([] (new-hash-state))
    ([state] (finish-hash-state state))
    ([state itm] (update-hash-unordered! state itm))))


(extend -str PersistentVector
  (fn [v]
    (apply str "[" (conj (transduce (interpose ", ") conj v) "]"))))




(extend -str Cons
  (fn [v]
    (apply str "(" (conj (transduce (interpose ", ") conj v) ")"))))

(extend -hash Cons
        (fn [v]
          (transduce ordered-hash-reducing-fn v)))

(extend -str PersistentList
  (fn [v]
    (apply str "(" (conj (transduce (interpose ", ") conj v) ")"))))

(extend -str LazySeq
  (fn [v]
    (apply str "(" (conj (transduce (interpose ", ") conj v) ")"))))

(extend -hash PersistentVector
  (fn [v]
    (transduce ordered-hash-reducing-fn v)))


(def stacklet->lazy-seq
  (fn [f]
    (let [val (f nil)]
      (if (identical? val :end)
        nil
        (cons val (lazy-seq* (fn [] (stacklet->lazy-seq f))))))))

(def sequence
  (fn
    ([data]
       (let [f (create-stacklet
                 (fn [h]
                   (reduce (fn ([h item] (h item) h)) h data)
                   (h :end)))]
          (stacklet->lazy-seq f)))
    ([xform data]
        (let [f (create-stacklet
                 (fn [h]
                   (transduce xform
                              (fn ([] h)
                                ([h item] (h item) h)
                                ([h] (h :end)))
                              data)))]
          (stacklet->lazy-seq f)))))

(extend -seq PersistentVector sequence)
(extend -seq Array sequence)



(def concat (fn [& args] (transduce cat conj args)))

(def defn (fn [nm & rest] `(def ~nm (fn ~nm ~@rest))))
(set-macro! defn)

(defn defmacro [nm & rest]
  `(do (defn ~nm ~@rest)
       (set-macro! ~nm)
       ~nm))
(set-macro! defmacro)


(defn +
  ([] 0)
  ([x] x)
  ([x y] (-add x y))
  ([x y z] (-add x (-add y z)))
  ([x y z & rest] (-add x (-add y (-add z (reduce -add 0 rest))))))

(defn -
  ([] 0)
  ([x] x)
  ([x y] (-sub x y))
  ([x y z] (-sub x (-sub y z)))
  ([x y z & rest] (-sub x (-sub y (-sub z (reduce -sub 0 rest))))))

(defn =
  ([x] true)
  ([x y] (eq x y))
  ([x y & rest] (if (eq x y)
                  (apply = y rest)
                  false)))

(def inc (fn [x] (+ x 1)))

(def dec (fn [x] (- x 1)))


(def slot-tp (create-type :slot [:val]))

(defn ->Slot [x]
  (let [inst (new slot-tp)]
    (set-field! inst :val x)))

(defn get-val [inst]
  (get-field inst :val))

(defn comp
  ([f] f)
  ([f1 f2]
     (fn [& args]
       (f1 (apply f2 args))))
  ([f1 f2 f3]
     (fn [& args]
       (f1 (f2 (apply f3 args))))))

(comment
(defmacro deftype [nm fields & body]
  (let [type-decl `(def ~nm (create-type ~(keyword (name nm))))
        field-syms (transduce (map (comp symbol name)) conj fields)
        ctor `(defn ~nm ~field-syms
                (let [inst (new ~nm)]
                  ~@(transduce
                     (map (fn [field]
                            `(set-field! inst ~field ~(symbol (name field)))))
                     conj
                     fields)
                  ~inst))]
    `(do ~type-decl
         ~ctor))))

(defn not [x]
  (if x false true))

(defmacro cond
  ([] nil)
  ([test then & clauses]
      `(if ~test
         ~then
         (cond ~@clauses))))

(defmacro try [& body]
  (loop [catch nil
         catch-sym nil
         body-items []
         finally nil
         body (seq body)]
    (let [form (first body)]
      (if form
        (if (not (seq? form))
          (recur catch catch-sym (conj body-items form) finally (next body))
          (let [head (first form)]
            (cond
             (= head 'catch) (if catch
                               (throw "Can only have one catch clause per try")
                               (recur (next (next form)) (first (next form)) body-items finally (next body)))
             (= head 'finally) (if finally
                                 (throw "Can only have one finally clause per try")
                                 (recur catch catch-sym body-items (next form) (next body)))
             :else (recur catch catch-sym (conj body-items form) finally (next body)))))
        `(-try-catch
          (fn [] ~@body-items)
          ~(if catch
             `(fn [~catch-sym] ~@catch)
             `(fn [] nil))

          (fn [] ~@finally))))))


(extend -count MapEntry (fn [self] 2))
(extend -nth MapEntry (fn [self idx not-found]
                          (cond (= idx 0) (-key self)
                                (= idx 1) (-val self)
                                :else not-found)))

(defn key [x]
  (-key x))

(defn val [x]
  (-val x))

(extend -reduce MapEntry indexed-reduce)

(extend -str MapEntry
        (fn [v]
            (apply str "[" (conj (transduce (interpose ", ") conj v) "]"))))

(extend -hash MapEntry
  (fn [v]
    (transduce ordered-hash-reducing-fn v)))

(extend -str PersistentHashMap
        (fn [v]
            (apply str "{" (conj (transduce (comp cat (interpose " ")) conj v) "}"))))

(extend -hash PersistentHashMap
        (fn [v]
          (transduce cat unordered-hash-reducing-fn v)))

(extend -hash Symbol
        (fn [v]
          (hash [(namespace v) (name v)])))

(extend -hash Keyword
        (fn [v]
          (hash [(namespace v) (name v)])))

(extend -str Keyword
  (fn [k]
    (if (namespace k)
      (str ":" (namespace k) "/" (name k))
      (str ":" (name k)))))


(defn get
  ([mp k]
     (get mp k nil))
  ([mp k not-found]
     (-val-at mp k not-found)))

(defmacro assert
  ([test]
     `(if ~test
        nil
        (throw "Assert failed")))
  ([test msg]
     `(if ~test
        nil
        (throw (str "Assert failed " ~msg)))))


(defmacro with-bindings [binds & body]
  `(do (push-binding-frame!)
       (reduce (fn [_ map-entry]
                 (set! (resolve (key map-entry)) (val map-entry)))
               nil
               (apply hashmap ~binds))
       (let [ret (do ~@body)]
         (pop-binding-frame!)
         ret)))

(def foo 42)
(set-dynamic! (resolve 'pixie.stdlib/foo))


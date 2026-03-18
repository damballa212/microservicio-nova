nova-dashboard-1        | ▲ Next.js 16.1.1
nova-dashboard-1        | - Local:         http://localhost:3000
nova-dashboard-1        | - Network:       http://0.0.0.0:3000
nova-dashboard-1        | 
nova-dashboard-1        | ✓ Starting...
nova-dashboard-1        | ✓ Ready in 247ms
nova-dashboard-1        | ▲ Next.js 16.1.1
nova-dashboard-1        | - Local:         http://localhost:3000
nova-dashboard-1        | - Network:       http://0.0.0.0:3000
nova-dashboard-1        | 
nova-dashboard-1        | ✓ Starting...
nova-dashboard-1        | ✓ Ready in 283ms
nova-dashboard-1        | ▲ Next.js 16.1.1
nova-dashboard-1        | - Local:         http://localhost:3000
nova-dashboard-1        | - Network:       http://0.0.0.0:3000
nova-dashboard-1        | 
nova-dashboard-1        | ✓ Starting...
nova-dashboard-1        | ✓ Ready in 353ms
nova-dashboard-1        | ▲ Next.js 16.1.1
nova-dashboard-1        | - Local:         http://localhost:3000
nova-dashboard-1        | - Network:       http://0.0.0.0:3000
nova-dashboard-1        | 
nova-dashboard-1        | ✓ Starting...
nova-dashboard-1        | ✓ Ready in 167ms
nova-api-1              | 🔭 OpenTelemetry Tracing Details 🔭
nova-api-1              | |  Phoenix Project: nova-ai
nova-api-1              | |  Span Processor: BatchSpanProcessor
nova-api-1              | |  Collector Endpoint: https://flowify-crm-phoenix.lsoqoe.easypanel.host/v1/traces
nova-api-1              | |  Transport: HTTP + protobuf
nova-api-1              | |  Transport Headers: {}
nova-api-1              | |  
nova-api-1              | |  Using a default SpanProcessor. `add_span_processor` will overwrite this default.
nova-api-1              | |  
nova-api-1              | |  `register` has set this TracerProvider as the global OpenTelemetry default.
nova-api-1              | |  To disable this behavior, call `register` with `set_global_tracer_provider=False`.
nova-api-1              | 
nova-api-1              | Traceback (most recent call last):
nova-api-1              |   File "/usr/local/bin/uvicorn", line 8, in <module>
nova-api-1              |     sys.exit(main())
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/click/core.py", line 1485, in __call__
nova-api-1              |     return self.main(*args, **kwargs)
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/click/core.py", line 1406, in main
nova-api-1              |     rv = self.invoke(ctx)
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/click/core.py", line 1269, in invoke
nova-api-1              |     return ctx.invoke(self.callback, **ctx.params)
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/click/core.py", line 824, in invoke
nova-api-1              |     return callback(*args, **kwargs)
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/uvicorn/main.py", line 424, in main
nova-api-1              |     run(
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/uvicorn/main.py", line 594, in run
nova-api-1              |     server.run()
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/uvicorn/server.py", line 67, in run
nova-api-1              |     return asyncio_run(self.serve(sockets=sockets), loop_factory=self.config.get_loop_factory())
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/uvicorn/_compat.py", line 60, in asyncio_run
nova-api-1              |     return loop.run_until_complete(main)
nova-api-1              |   File "uvloop/loop.pyx", line 1518, in uvloop.loop.Loop.run_until_complete
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/uvicorn/server.py", line 71, in serve
nova-api-1              |     await self._serve(sockets)
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/uvicorn/server.py", line 78, in _serve
nova-api-1              |     config.load()
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/uvicorn/config.py", line 439, in load
nova-api-1              |     self.loaded_app = import_from_string(self.app)
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/uvicorn/importer.py", line 19, in import_from_string
nova-api-1              |     module = importlib.import_module(module_str)
nova-api-1              |   File "/usr/local/lib/python3.10/importlib/__init__.py", line 126, in import_module
nova-api-1              |     return _bootstrap._gcd_import(name[level:], package, level)
nova-api-1              |   File "<frozen importlib._bootstrap>", line 1050, in _gcd_import
nova-api-1              |   File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
nova-api-1              |   File "<frozen importlib._bootstrap>", line 1006, in _find_and_load_unlocked
nova-api-1              |   File "<frozen importlib._bootstrap>", line 688, in _load_unlocked
nova-api-1              |   File "<frozen importlib._bootstrap_external>", line 883, in exec_module
nova-api-1              |   File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
nova-api-1              |   File "/app/src/main.py", line 149, in <module>
nova-api-1              |     ) = _load_runtime_deps()
nova-api-1              |   File "/app/src/main.py", line 111, in _load_runtime_deps
nova-api-1              |     from src.api.router import router
nova-api-1              |   File "/app/src/api/__init__.py", line 7, in <module>
nova-api-1              |     from src.api.router import router
nova-api-1              |   File "/app/src/api/router.py", line 41, in <module>
nova-api-1              |     from src.graph.builder import enqueue_chatbot, get_graph_diagram, get_queue_status, run_chatbot
nova-api-1              |   File "/app/src/graph/__init__.py", line 7, in <module>
nova-api-1              |     from src.graph.builder import build_chatbot_graph, chatbot_graph
nova-api-1              |   File "/app/src/graph/builder.py", line 22, in <module>
nova-api-1              |     from src.nodes.ai_agent import generate_response
nova-api-1              |   File "/app/src/nodes/__init__.py", line 8, in <module>
nova-api-1              |     from src.nodes.ai_agent import generate_response
nova-api-1              |   File "/app/src/nodes/ai_agent.py", line 31, in <module>
nova-api-1              |     from src.nodes.tools import inventory_lookup, rag_search, semantic_memory_search
nova-api-1              |   File "/app/src/nodes/tools.py", line 7, in <module>
nova-api-1              |     from src.rag.vector_store import reranked_search
nova-api-1              |   File "/app/src/rag/vector_store.py", line 342
nova-api-1              |     \"\"\"Elimina completamente un documento y sus chunks.\"\"\"
nova-api-1              |      ^
nova-api-1              | SyntaxError: unexpected character after line continuation character
nova-episodes-worker-1  | 2025-12-27 01:58:43 [info     ] Iniciando Worker de Episodios Semánticos
nova-episodes-worker-1  | 2025-12-27 01:58:43 [info     ] Pool de conexiones Redis creado url=redis://default:marlon212@flowify-crm_redis:6379
nova-worker-1           | Traceback (most recent call last):
nova-worker-1           |   File "/usr/local/lib/python3.10/runpy.py", line 196, in _run_module_as_main
nova-worker-1           |     return _run_code(code, main_globals, None,
nova-worker-1           |   File "/usr/local/lib/python3.10/runpy.py", line 86, in _run_code
nova-worker-1           |     exec(code, run_globals)
nova-worker-1           |   File "/app/src/rag/worker.py", line 10, in <module>
nova-worker-1           |     from src.rag.vector_store import insert_rows, upsert_chunks, upsert_metadata
nova-worker-1           |   File "/app/src/rag/vector_store.py", line 342
nova-worker-1           |     \"\"\"Elimina completamente un documento y sus chunks.\"\"\"
nova-worker-1           |      ^
nova-worker-1           | SyntaxError: unexpected character after line continuation character
nova-worker-1           | Traceback (most recent call last):
nova-worker-1           |   File "/usr/local/lib/python3.10/runpy.py", line 196, in _run_module_as_main
nova-worker-1           |     return _run_code(code, main_globals, None,
nova-worker-1           |   File "/usr/local/lib/python3.10/runpy.py", line 86, in _run_code
nova-worker-1           |     exec(code, run_globals)
nova-worker-1           |   File "/app/src/rag/worker.py", line 10, in <module>
nova-worker-1           |     from src.rag.vector_store import insert_rows, upsert_chunks, upsert_metadata
nova-worker-1           |   File "/app/src/rag/vector_store.py", line 342
nova-worker-1           |     \"\"\"Elimina completamente un documento y sus chunks.\"\"\"
nova-worker-1           |      ^
nova-worker-1           | SyntaxError: unexpected character after line continuation character
nova-worker-1           | Traceback (most recent call last):
nova-worker-1           |   File "/usr/local/lib/python3.10/runpy.py", line 196, in _run_module_as_main
nova-worker-1           |     return _run_code(code, main_globals, None,
nova-worker-1           |   File "/usr/local/lib/python3.10/runpy.py", line 86, in _run_code
nova-worker-1           |     exec(code, run_globals)
nova-worker-1           |   File "/app/src/rag/worker.py", line 10, in <module>
nova-worker-1           |     from src.rag.vector_store import insert_rows, upsert_chunks, upsert_metadata
nova-worker-1           |   File "/app/src/rag/vector_store.py", line 342
nova-worker-1           |     \"\"\"Elimina completamente un documento y sus chunks.\"\"\"
nova-worker-1           |      ^
nova-worker-1           | SyntaxError: unexpected character after line continuation character
nova-worker-1 exited with code 1
nova-api-1              | 🔭 OpenTelemetry Tracing Details 🔭
nova-api-1              | |  Phoenix Project: nova-ai
nova-api-1              | |  Span Processor: BatchSpanProcessor
nova-api-1              | |  Collector Endpoint: https://flowify-crm-phoenix.lsoqoe.easypanel.host/v1/traces
nova-api-1              | |  Transport: HTTP + protobuf
nova-api-1              | |  Transport Headers: {}
nova-api-1              | |  
nova-api-1              | |  Using a default SpanProcessor. `add_span_processor` will overwrite this default.
nova-api-1              | |  
nova-api-1              | |  `register` has set this TracerProvider as the global OpenTelemetry default.
nova-api-1              | |  To disable this behavior, call `register` with `set_global_tracer_provider=False`.
nova-api-1              | 
nova-api-1              | Traceback (most recent call last):
nova-api-1              |   File "/usr/local/bin/uvicorn", line 8, in <module>
nova-api-1              |     sys.exit(main())
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/click/core.py", line 1485, in __call__
nova-api-1              |     return self.main(*args, **kwargs)
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/click/core.py", line 1406, in main
nova-api-1              |     rv = self.invoke(ctx)
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/click/core.py", line 1269, in invoke
nova-api-1              |     return ctx.invoke(self.callback, **ctx.params)
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/click/core.py", line 824, in invoke
nova-api-1              |     return callback(*args, **kwargs)
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/uvicorn/main.py", line 424, in main
nova-api-1              |     run(
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/uvicorn/main.py", line 594, in run
nova-api-1              |     server.run()
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/uvicorn/server.py", line 67, in run
nova-api-1              |     return asyncio_run(self.serve(sockets=sockets), loop_factory=self.config.get_loop_factory())
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/uvicorn/_compat.py", line 60, in asyncio_run
nova-api-1              |     return loop.run_until_complete(main)
nova-api-1              |   File "uvloop/loop.pyx", line 1518, in uvloop.loop.Loop.run_until_complete
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/uvicorn/server.py", line 71, in serve
nova-api-1              |     await self._serve(sockets)
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/uvicorn/server.py", line 78, in _serve
nova-api-1              |     config.load()
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/uvicorn/config.py", line 439, in load
nova-api-1              |     self.loaded_app = import_from_string(self.app)
nova-api-1              |   File "/usr/local/lib/python3.10/site-packages/uvicorn/importer.py", line 19, in import_from_string
nova-api-1              |     module = importlib.import_module(module_str)
nova-api-1              |   File "/usr/local/lib/python3.10/importlib/__init__.py", line 126, in import_module
nova-api-1              |     return _bootstrap._gcd_import(name[level:], package, level)
nova-api-1              |   File "<frozen importlib._bootstrap>", line 1050, in _gcd_import
nova-api-1              |   File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
nova-api-1              |   File "<frozen importlib._bootstrap>", line 1006, in _find_and_load_unlocked
nova-api-1              |   File "<frozen importlib._bootstrap>", line 688, in _load_unlocked
nova-api-1              |   File "<frozen importlib._bootstrap_external>", line 883, in exec_module
nova-api-1              |   File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
nova-api-1              |   File "/app/src/main.py", line 149, in <module>
nova-api-1              |     ) = _load_runtime_deps()
nova-api-1              |   File "/app/src/main.py", line 111, in _load_runtime_deps
nova-api-1              |     from src.api.router import router
nova-api-1              |   File "/app/src/api/__init__.py", line 7, in <module>
nova-api-1              |     from src.api.router import router
nova-api-1              |   File "/app/src/api/router.py", line 41, in <module>
nova-api-1              |     from src.graph.builder import enqueue_chatbot, get_graph_diagram, get_queue_status, run_chatbot
nova-api-1              |   File "/app/src/graph/__init__.py", line 7, in <module>
nova-api-1              |     from src.graph.builder import build_chatbot_graph, chatbot_graph
nova-api-1              |   File "/app/src/graph/builder.py", line 22, in <module>
nova-api-1              |     from src.nodes.ai_agent import generate_response
nova-api-1              |   File "/app/src/nodes/__init__.py", line 8, in <module>
nova-api-1              |     from src.nodes.ai_agent import generate_response
nova-api-1              |   File "/app/src/nodes/ai_agent.py", line 31, in <module>
nova-api-1              |     from src.nodes.tools import inventory_lookup, rag_search, semantic_memory_search
nova-api-1              |   File "/app/src/nodes/tools.py", line 7, in <module>
nova-api-1              |     from src.rag.vector_store import reranked_search
nova-api-1              |   File "/app/src/rag/vector_store.py", line 342
nova-api-1              |     \"\"\"Elimina completamente un documento y sus chunks.\"\"\"
nova-api-1              |      ^
nova-api-1              | SyntaxError: unexpected character after line continuation character
nova-worker-1           | Traceback (most recent call last):
nova-worker-1           |   File "/usr/local/lib/python3.10/runpy.py", line 196, in _run_module_as_main
nova-worker-1           |     return _run_code(code, main_globals, None,
nova-worker-1           |   File "/usr/local/lib/python3.10/runpy.py", line 86, in _run_code
nova-worker-1           |     exec(code, run_globals)
nova-worker-1           |   File "/app/src/rag/worker.py", line 10, in <module>
nova-worker-1           |     from src.rag.vector_store import insert_rows, upsert_chunks, upsert_metadata
nova-worker-1           |   File "/app/src/rag/vector_store.py", line 342
nova-worker-1           |     \"\"\"Elimina completamente un documento y sus chunks.\"\"\"
nova-worker-1           |      ^
nova-worker-1           | SyntaxError: unexpected character after line continuation character
nova-worker-1 exited with code 1
nova-api-1 exited with code 1
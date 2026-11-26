"""Compatible entrypoint: read-only preflight; --resume starts the supervised mesh queue."""
import sys
import mesh_selection_queue
if __name__=='__main__':
 if '--resume' in sys.argv:sys.argv[sys.argv.index('--resume')]='--run'
 mesh_selection_queue.main()

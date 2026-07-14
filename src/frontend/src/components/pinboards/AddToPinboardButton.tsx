import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { Loader2, Pin } from 'lucide-react';
import { Button } from '@/components/ui';
import {
  useAddPinboardItem,
  usePinboards,
  type AddPinboardItemRequest,
} from '@/services';

export function AddToPinboardButton({
  items,
  label = 'Add to pinboard',
}: {
  items: AddPinboardItemRequest[];
  label?: string;
}) {
  const { data: pinboards = [] } = usePinboards();
  const addItem = useAddPinboardItem();

  const addTo = async (pinboardId: string) => {
    for (const item of items) {
      try {
        await addItem.mutateAsync({ pinboardId, item });
      } catch (error) {
        // A duplicate is harmless from this small row-level affordance.
        if (!(error instanceof Error && error.message.includes('already on this pinboard'))) {
          throw error;
        }
      }
    }
  };

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <Button type="button" variant="ghost" size="icon" aria-label={label}>
          {addItem.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Pin className="h-4 w-4" />
          )}
        </Button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="z-[100] min-w-[12rem] rounded-xl border border-black/[0.08] bg-white p-1 shadow-lg"
          sideOffset={8}
          align="end"
        >
          {pinboards.length === 0 ? (
            <DropdownMenu.Item disabled className="px-3 py-2 text-sm text-ink-tertiary">
              Create a pinboard first
            </DropdownMenu.Item>
          ) : pinboards.map((pinboard) => (
            <DropdownMenu.Item
              key={pinboard.id}
              className="cursor-pointer rounded-lg px-3 py-2 text-sm outline-none hover:bg-surface-muted focus:bg-surface-muted"
              onSelect={() => void addTo(pinboard.id)}
            >
              {pinboard.name}
            </DropdownMenu.Item>
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

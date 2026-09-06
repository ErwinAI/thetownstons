-- Lock the wiki Main Page. Confirmed users may still edit everything else.

update public.pages
set locked = true
where slug = 'Main_Page'
   or fold_key = 'main page';

update public.site_settings
set value = 'true'::jsonb
where key = 'open_edits';
